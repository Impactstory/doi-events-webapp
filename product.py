from util import elapsed

import requests

from time import time
import inspect
import sys
import re
from lxml import html
from threading import Thread
import urlparse


def get_oa_url(url, verbose=False):
    if verbose:
        print "getting URL: ", url

    r = requests.get(url, timeout=5)  # timeout in secs
    page = r.text

    page = page.replace("&nbsp;", " ")  # otherwise starts-with for lxml doesn't work
    tree = html.fromstring(page)

    page_words = " ".join(tree.xpath("//body")[0].text_content().lower().split())
    if page_says_closed(page_words):
        return None

    pdf_download_link = find_pdf_download_link(tree, verbose)
    if pdf_download_link is not None:
        return urlparse.urljoin(r.url, pdf_download_link.attrib["href"])

    return None




def find_pdf_download_link(tree, verbose=False):
    links = tree.xpath("//a")
    for link in links:
        link_text = link.text_content().strip().lower()
        if verbose:
            print "trying with link text: ", link_text

        try:
            link_target = link.attrib["href"]
        except KeyError:
            # if the link doesn't point nowhere, it's no use to us
            if verbose:
                print "this link doesn't point anywhere. abandoning it."

            continue

        """
        The download link doesn't have PDF at the end, but the download button is nice and clear.

        =https://works.bepress.com/ethan_white/45/
        =https://works.bepress.com/ethan_white/45/download/

        =https://works.bepress.com/ethan_white/27/
        =None

        =http://ro.uow.edu.au/aiimpapers/269/
        =http://ro.uow.edu.au/cgi/viewcontent.cgi?article=1268&context=aiimpapers
        """
        if link_text == "download":
            return link


        """
        download text has the word "download" it is somewhere, and the link is pointing to a PDF file:

        =http://eprints.whiterose.ac.uk/77866/
        =http://eprints.whiterose.ac.uk/77866/25/ggge20346_with_coversheet.pdf

        note that researchgate can return various different things after the ? part of url.
        makes for fussy testing but shouldn't matter much in production
        =https://www.researchgate.net/publication/235915359_Promotion_of_Virtual_Research_Communities_in_CHAIN
        =https://www.researchgate.net/profile/Bruce_Becker4/publication/235915359_Promotion_of_Virtual_Research_Communities_in_CHAIN/links/0912f5141bd165b4ef000000.pdf?origin=publication_detail
        """
        if "download" in link_text:
            return link



        """
        download link anchor text is something like foobar.pdf

        =http://hdl.handle.net/1893/372
        =http://dspace.stir.ac.uk/bitstream/1893/372/1/Corley%20COGNITION%202007.pdf

        =https://research-repository.st-andrews.ac.uk/handle/10023/7421
        =https://research-repository.st-andrews.ac.uk/bitstream/handle/10023/7421/Manuscripts_edited_final.pdf?sequence=1&isAllowed=y
        """
        if len(re.findall(ur".\.pdf\b", link_text)):
            return link



    return None



def page_says_closed(page_words):

    # "not in this repo" words
    blacklist_phrases = [

        # =https://lirias.kuleuven.be/handle/123456789/9821
        # =None
        "request a copy",

        # =http://eprints.gla.ac.uk/20877/
        # =None

        "full text not available",
        "file restricted",
        "full text not currently available",
        "full-text and supplementary files are not available",
        "no files associated with this item",

        # not sure if we should keep this one, danger of false negs
        # =http://nora.nerc.ac.uk/8783/
        # =None
        "(login required)",

        # =http://sro.sussex.ac.uk/54348/
        # =None
        # =http://researchbank.acu.edu.au/fea_pub/434/
        # =None
        "admin only"
    ]

    # paywall words
    blacklist_phrases += [
        # =http://www.cell.com/trends/genetics/abstract/S0168-9525(07)00023-6
        # =None
        "purchase access"
    ]

    for phrase in blacklist_phrases:
        if phrase in page_words:
            return True

    return False


def is_pdf_url(url):
    return len(re.findall(ur"\.pdf\b", url)) > 0


class Tests(object):
    def __init__(self):
        self.passed = []
        self.elapsed = 0


    def run(self):
        start = time()
        
        # get all the test pairs
        this_module = sys.modules[__name__]
        file_source = inspect.getsource(this_module)
        p = re.compile(ur'^[\s#]*=(.+)\n[\s#]*=(.+)', re.MULTILINE)
        test_pairs = re.findall(p, file_source)
        
        # start a thread for each test pair,
        # and save the results in a single shared list, test_results
        threads = []
        test_results = []
        for url, expected_output in test_pairs:
            verbose = False
            if url.startswith("verbose: "):
                verbose = True
                url = url.replace("verbose: ", "")

            process = Thread(target=test_url_for_threading, args=[url, expected_output, verbose, test_results])
            process.start()
            threads.append(process)
    
        # wait till all work is done
        for process in threads:
            process.join()

        # store the test results
        self.results = test_results
        self.elapsed = elapsed(start)


def test_url_for_threading(url, expected_output, verbose, all_test_results):
    res = test_url(url, expected_output, verbose)
    all_test_results.append(res)
    return all_test_results

def test_url(url, expected_output, verbose):

    if expected_output == "None":
        expected_output = None

    my_start = time()
    result = get_oa_url(url, verbose)

    return {
        "elapsed": elapsed(my_start),
        "url": url,
        "result": result,
        "expected": expected_output,
        "passed": result == expected_output
    }



