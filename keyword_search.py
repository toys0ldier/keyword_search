import os, shutil, html, sys, json, re
from datetime import datetime

class OperationError(Exception):
    
    def __init__(self, message="Whoops! We're missing some arguments!"):
        self.message = message
        super().__init__(self.message)
        
def showHelp():
    print('''\nUsage: wordlist=[path/to/keyword_file] target=[path/to/search_directory]
       output=[path_to/output_directory] (optional) [d2] (optional)''')
    
    print('\nAvailable flags:')
    print('-h, --help                         ->   show this help message and exit')
    print('wordlist=[path_to/keyword_file]    ->   keyword file (one keyword per line)')
    print('target=[path_to/search_directory]  ->   folder containing items to be searched')
    print('output=[path_to/output_directory   ->   folder to output results (optional')
    print('d2                                 ->   depth of folder (optional, 1 if omitted)')
        
    sys.exit()
    
def scanTree(path):
    try:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                yield from scanTree(entry)
            else:
                yield entry
    except PermissionError:
        pass

def formatSize(size):
    if size < 1048576:
        return '{:,}'.format(round(size / 1024, 2)) + ' KB'
    elif size > 1048576 and size < 1073741824:
        return '{:,}'.format(round(size / 1048576, 2)) + ' MB'
    else:
        return '{:,}'.format(round(size / 1073741824, 2)) + ' GB'
    
def saveHtml(results, output):
    fileOut = os.path.join(output, results['target'] + '.html')
    with open(fileOut + '_KeywordSearch.html', 'w') as outFile:
        print('\nPreparing output file and saving results for: %s' % results['target'])
        css = '''
            <style>
                body {
                    font-family: "Helvetica", "Arial", sans-serif;
                    color: #51585a;
                    font-size: 12px;
                    padding-top: 20px;
                    padding-left: 40px;
                    padding-right: 40px;
                }
                h3, h4 {
                    text-align: center;
                }
                table {
                    font-family: "Helvetica", "Arial", sans-serif;
                    color: #51585a;
                    font-size: 12px;
                    table-layout: fixed;
                    width: 100%;
                }
                th, td {
                    text-align: left;
                    word-wrap: break-word;
                }
                .meta-title {
                    width: 7%;
                }
                .line {
                    width: 5%;
                }
                .match {
                    width: 15%;
                }
                .text {
                    width: 75%;
                }
                .head {
                    font-weight: bold;
                }
                .highlight-match {
                    color: #eb4034;
                    font-weight: bold;
                }
            </style>
            '''
        outFile.write('<title>%s Keyword Search</title>' % results['target'])
        outFile.write(css)
        outFile.write('<h3>Keyword Results for %s</h3>' % results['target'])
        outFile.write('<h4>Generated: %s</h4>' % datetime.now().strftime('%Y-%m-%d %H:%M:%S CST'))
        for record in results['data']:
                record_data = []
                for keyword_match in record['results']:
                    try:
                        restat = '.{1,250}%s.{1,250}' % keyword_match['match']
                        excerpt = re.search(restat, keyword_match['text'].lower())
                        if excerpt:
                            record_data.append({
                                'line': keyword_match['line'],
                                'match': keyword_match['match'],
                                'text': re.sub(keyword_match['match'], '<span class="highlight-match">%s</span>' % keyword_match['match'], html.escape(excerpt[0]))
                            })
                    except Exception:
                        pass
                if record_data:
                    relpath_list = os.path.normpath(record['filepath']).split(os.path.sep)
                    relpath = os.path.join(*relpath_list[relpath_list.index(results['target']) + 1:])
                    fileMeta = '''
                            <table>
                                <tr>
                                    <td class="meta-title"><span class="head">Filename:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                                <tr>
                                    <td class="meta-title"><span class="head">Filepath:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                                <tr>
                                    <td class="meta-title"><span class="head">File Size:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                                <tr>
                                    <td class="meta-title"><span class="head">Modified:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                                <tr>
                                    <td class="meta-title"><span class="head">Accessed:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                                <tr>
                                    <td class="meta-title"><span class="head">Created:</span></td>
                                    <td class="meta-data">&nbsp;%s</td>
                                </tr>
                            </table>
                    ''' % (record['filename'], 
                           relpath, 
                           formatSize(record['filesize']), 
                           datetime.fromtimestamp(record['mtime']).strftime('%Y-%m-%d %H:%M:%S'),
                           datetime.fromtimestamp(record['atime']).strftime('%Y-%m-%d %H:%M:%S'),
                           datetime.fromtimestamp(record['ctime']).strftime('%Y-%m-%d %H:%M:%S'))
                    outFile.write(fileMeta)
                    outFile.write('''<br />
                            <table>
                                <tr>
                                    <th class="line">Line #</th>
                                    <th class="match">Match</th>
                                    <th class="text">Line Contents (500 Character Limit)</th>
                                </tr>''')
                    for r in record_data:
                        outFile.write('''
                                        <tr>
                                            <td class="line">%s</td>
                                            <td class="match">[ <span class="highlight-match">%s</span> ]</td>
                                            <td class="text">%s
                                        </tr>
                                        ''' % (r['line'], r['match'], r['text']))
                    outFile.write('</table><br /><br />')
    
def saveJson(results, output):
    with open(os.path.join(output, 'keyword_results.json'), 'w') as outFile:
        outFile.write(json.dumps(results, indent=4))

def scanFile(wordlist, folderName, entry, output):
    results = []
    data = {
        'filename': entry.name,
        'filepath': entry.path,
        'filesize': entry.stat().st_size,
        'mtime': entry.stat().st_mtime,
        'ctime': entry.stat().st_ctime,
        'atime': entry.stat().st_atime,
        'results': []
    }
    with open(entry.path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        lines = f.read().splitlines()
        if lines:
            for i, line in enumerate(lines):
                for word in wordlist:
                    if word.lower() in line.lower():
                        data['results'].append({
                            'line': i, 
                            'match': word,
                            'text': line if len(line) <= 10000 else line[0:10000]
                        })
    if data['results']:
        results.append(data)
        try:
            outdir = os.path.join(output, folderName)
            if not os.path.exists(outdir):
                os.mkdir(outdir)
            shutil.copy(entry.path, outdir)
        except Exception:
            print('Failed to copy file: %s' % entry.path)
            pass
        return results
    return ''

def scanSingle(first_level):
    results = []
    for entry in os.scandir(first_level):
        if entry.is_dir() and entry.name != 'Keyword_Results':
            print('[+] Searching folder: %s' % entry.name)
            for sub_entry in scanTree(entry.path):
                try:
                    if sub_entry.is_file() and sub_entry.stat().st_size <= 104857600: # only read files under 100mb:
                        try:
                            data = scanFile(wordlist, entry.name, sub_entry, output)
                            if data:
                                results.extend(data)
                        except Exception as err:
                            print('Error reading: %s' % sub_entry.name)
                            print('Error text: %s' % str(err))
                            pass
                except Exception:
                    pass
    return results
                    
def startScan(target):
    results = {
        'target': os.path.splitext(os.path.split(target)[1])[0],
        'data': []
    }
    if depth == 2:
        for first_level in os.scandir(target):
            if first_level.is_dir() and first_level.name != 'Keyword_Results':
                print('Working in: %s' % first_level.name)
                data = scanSingle(first_level.path)
                if data:
                    results['data'].extend(data)
    else:
        data = scanSingle(target)
        if data:
            results['data'].extend(data)
        
    if results['data']:
        saveJson(results, output)
        saveHtml(results, output)
        print('Process completed successfully!')
    else:
        print('\nProcess completed successfully but no keywords found in target folder(s)!')

def defineWordlist(wordFile):
    with open(wordFile, 'r') as kwdFile:
        return kwdFile.read().splitlines()

def main():
    global depth, wordlist, output
    output, wordlist, target = ('', '', '')
    depth = 1
    print('keyword_search, v%s created by toys0ldier: github.com/toys0ldier' % verNum)
    if sys.argv[1] == '-h' or sys.argv[1] == '--help':
        showHelp()
    for arg in sys.argv[1:]:
        if arg == 'd2':
            depth = 2
        if 'wordlist=' in arg:
            wordlistFile = arg.split('=')[1]
            wordlist = defineWordlist(arg.split('=')[1])
        if 'target=' in arg:
            target = arg.split('=')[1]
        if 'output=' in arg:
            output = arg.split('=')[1]
    if not wordlist:
        OperationError('No wordlist specified. Retry with the wordlist= flag and a path to your wordlist file!')
    if not target:
        OperationError('No target specified. Retry with the target= flag and a path to the folder to be searched!')
    if not output:
        output = os.path.join(target, 'Keyword_Results')
    else:
        output = os.path.join(output, 'Keyword_Results')
    if not os.path.exists(output):
        os.mkdir(output)
    if wordlist and os.path.isdir(target):
        print('\nLoaded %s keywords from wordlist: %s' % (len(wordlist), os.path.split(wordlistFile)[1]))
        print('Starting keyword search for target: %s\n' % os.path.split(target)[1])
        startScan(target)

if __name__ == '__main__':
    
    verNum = '0.0.1b'
    main()