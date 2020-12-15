import subprocess

child_process = subprocess.Popen("curl command", shell=True)

child_process.wait()
print('done')


def get_csv_url(file_name):
    filename = Path(file_name)
    ftpCommand = "STOR %s"%filename.name;
    csv_url = "http://project-ethiopia.000webhostapp.com/client_software/" + file_name
    
    with FTP('', '', '') as ftp:
        ftp.cwd('/public_html/client_software')
        with open(file_name, 'rb') as f:
            ftpResponse = ftp.storbinary(ftpCommand, fp=f)
            print(ftpResponse)
    
    return csv_url
