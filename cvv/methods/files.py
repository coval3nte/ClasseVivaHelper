"""files"""
from os import path, makedirs
from re import findall
from requests import get
from lxml import html
from ..data_types import File


class Files:
    """files downloader class"""

    def __init__(self, cvv):
        self.cvv = cvv

    def _do_files(self, params):
        files = get(self.cvv.endpoint +
                    '/fml/app/default/didattica_genitori_new.php',
                    params=params,
                    cookies=self.cvv.cookies,
                    headers=self.cvv.headers
                    )

        if files.status_code != 200:
            raise self.cvv.GenericError
        return files.text

    def _do_pages(self):
        params = {
            'p': 1
        }

        files_pages = []
        init = self._do_files(params)
        files_pages.append(init)
        length = int(init.split("Pagina 1/")[1][0:1]) - 1

        for _ in range(length):
            params['p'] += 1
            files_pages.append(self._do_files(params))

        return files_pages

    def download_file(self, filename, contenuto_id, cksum):
        """download file"""
        params = {
            'a': 'downloadContenuto',
            'contenuto_id': contenuto_id,
            'cksum': cksum
        }
        resp = get(self.cvv.endpoint +
                   '/fml/app/default/didattica_genitori.php',
                   params=params,
                   cookies=self.cvv.cookies,
                   headers=self.cvv.headers)
        if resp.status_code != 200:
            raise self.cvv.GenericError

        save_folder = self.cvv.args.save_folder.rstrip('/')
        if not path.exists(save_folder):
            makedirs(save_folder)
        with open(save_folder+"/"+filename+'.' +
                  findall("filename=(.+)",
                          resp.headers['content-disposition']
                          )[0].split('.')[-1],
                  'wb') as file:
            file.write(resp.content)

    def retrieve_files(self):
        """retrieve files"""
        files_pages = self._do_pages()
        files_list = []

        for files in files_pages:
            tree = html.fromstring(files)
            trs = tree.xpath('//*[@id="data_table"]/*[@contenuto_id]')

            for xpath_tr in trs:
                tds = xpath_tr.xpath('td')
                files_list.append(File(
                    xpath_tr.xpath('@contenuto_id')[0],
                    xpath_tr.xpath('*/div/@cksum')[0],
                    tds[1].text_content().strip(),
                    path.splitext(tds[3].text_content(
                    ).strip().split('\n')[0].rstrip())[0],
                    tds[5].text_content().strip())
                )

        return files_list
