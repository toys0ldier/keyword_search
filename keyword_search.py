'''
Usage: wordlist=[path/to/keyword_file] target=[path/to/search_directory] output=[path/to/output_directory] (optional)
'''

import os, shutil, html, sys, json, re
from datetime import datetime

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
        print('[+] Preparing output file and saving results for: %s' % results['target'])
        css = '''
                <style>
                body, table {
                    font-family: "Helvetica", "Arial", sans-serif;
                    color: #51585a;
                    font-size: 14px;
                    padding-top: 20px;
                    padding-left: 40px;
                    padding-right: 40px;
                    width: 100%;
                }
                h3 h4 {
                    margin: auto;
                }
                th td {
                    text-align: left;
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
        for record in results['data']:
                results = []
                for result in record['results']:
                    restat = '.{1,250}%s.{1,250}' % result['match']
                    excerpt = re.search(restat, result['text'].lower())
                    if excerpt:
                        results.append({
                            'line': result['line'],
                            'match': result['match'],
                            'text': re.sub(result['match'], '<span class="highlight-match">%s</span>' % result['match'], html.escape(excerpt[0]))
                        })
                if results:
                    relpath_list = os.path.normpath(record['filepath']).split(os.path.sep)
                    relpath = relpath_list[relpath_list.index(results['target']) + 1:]
                    outFile.write('<h3>Keyword Results for %s</h3>' % results['target'])
                    outFile.write('<h4>Generated: %s</h5>' % datetime.now().strftime('%Y-%m-%d %H:%M:%S CST'))
                    outFile.write('<span class="head">Filename:</span>&nbsp;%s<br />' % record['filename'])
                    outFile.write('<span class="head">Filepath (Relative):</span>&nbsp;%s<br />' % relpath)
                    outFile.write('<span class="head">File Size:</span>&nbsp;%s<br />' % formatSize(record['filesize']))
                    outFile.write('<span class="head">Modified:</span>&nbsp;%s<br />' % datetime.fromtimestamp(record['mtime']).strftime('%Y-%m-%d %H:%M:%S'))
                    outFile.write('<span class="head">Accessed:</span>&nbsp;%s<br />' % datetime.fromtimestamp(record['atime']).strftime('%Y-%m-%d %H:%M:%S'))
                    outFile.write('<span class="head">Created:</span>&nbsp;%s<br />' % datetime.fromtimestamp(record['ctime']).strftime('%Y-%m-%d %H:%M:%S'))
                    outFile.write('''<br />
                            <table>
                                <tr>
                                    <th class="line">Line #</th>
                                    <th class="match">Match</th>
                                    <th class="text">Line Contents (500 Character Limit)</th>
                                </tr>''')
                    for r in results:
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

def startScan(wordlist, target, output):
    results = []
    for first_level in os.scandir(target):
        if first_level.is_dir():
            print('Working in: %s' % first_level.name)
            for sub_entry in os.scandir(first_level.path):
                if sub_entry.is_dir():
                    print('Active droplet: %s' % sub_entry.name)
                    sub_results = {
                        'target': sub_entry.name,
                        'data': []
                    }
                    for entry in scanTree(sub_entry.path):
                        try:
                            if entry.is_file() and entry.stat().st_size <= 104857600: # only read files under 100mb:
                                try:
                                    sub_results['data'].extend(scanFile(wordlist, sub_entry.name, entry, output))
                                except Exception as err:
                                    print('Error reading: %s' % entry.name)
                                    print('Error text: %s' % str(err))
                                    pass
                        except Exception:
                            pass
                    results.append(sub_results)
                    saveHtml(sub_results, output)
    saveJson(results, output)

def defineWordlist(wordFile):
    with open(wordFile, 'r') as kwdFile:
        return kwdFile.read().splitlines()

def main():
    output = ''
    for arg in sys.argv[1:]:
        if arg.startswith('wordlist='):
            wordlist = defineWordlist(arg.split('wordlist=')[1])
        if arg.startswith('target='):
            target = arg.split('target=')[1]
        if arg.startswith('output='):
            output = arg.split('output=')[1]
    if not output:
        output = os.path.join(target, 'Keyword_Results')
        os.mkdir(output)
    if wordlist and target:
        startScan(wordlist, target, output)
            

if __name__ == '__main__':
    
    main()