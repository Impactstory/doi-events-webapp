from Bio import Entrez


def get_results_from_author_name(author_name):
    Entrez.email = "team@impactstory.org"
    handle = Entrez.esearch(db="pubmed", term=author_name)
    result = Entrez.read(handle)
    handle.close()
    print result
    return result

def get_pmids_from_author_name(author_name):
    result = get_results_from_author_name(author_name)
    return result["IdList"]
