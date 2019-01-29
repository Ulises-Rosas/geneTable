import re
import urllib.request
import argparse
import matplotlib.pyplot as plt
from collections import Counter


parser = argparse.ArgumentParser(description="Retrieve information by using API's utils")

parser.add_argument('string', metavar='Term',
                    help='Boolean string which will be used to search sequences')
parser.add_argument('-type', metavar="Retrieval type",
                    default = "fasta",
                    help='<fasta, gb, ...>. Default: fasta')
parser.add_argument('-db', metavar="Database",
                    default = "nuccore",
                    help='<nuccore, sra, ...>. Default: nuccore')
parser.add_argument('-markers', metavar="Markers",
                    default = "",
                    help='This option only works if Database is "nuccore". String storing markers (e.g. "COI,COX")')
parser.add_argument('-Lmin', metavar="Minimum-Length",
                    default = "",
                    help='This option only works if Database is "nuccore". Minimun length for downloaded sequences')

parser.add_argument('-Lmax', metavar="Maximun-Length",
                    default = "",
                    help='This option only works if Database is "nuccore". Maximun length for downloaded sequences')
parser.add_argument('-ite',
                    action = 'store_true',
                    help='''This option only works if Retrieval type is "gb". This option allows to filter only
                    species-level gg files of both term and group (see below).''')
parser.add_argument('-group', metavar="Iterative",
                    default = "Genus",
                    help='''This option only works if Iterative mode is selected. This option allows to find only
                     species-level "gb" files of a group selected (e.g. Genus). If there was not species-level "gb"
                      files, this value will shift to a higher taxonomic rank (e.g. Family). Default: Genus''')
parser.add_argument('-out', metavar="Iterative",
                    default = "",
                    help='''This option only works if Iterative mode is selected. File name of species-level "gb"
                     files. Default: output.gb''')
parser.add_argument('-ids',
                    action = 'store_true',
                    help='''Get ids of a given request''')
parser.add_argument('--plot',
                    action = 'store_true',
                    help='''plot in some specific functions''')
parser.add_argument('-cache', metavar="Rate",
                    default = 200,
                    help='Number of sequences downloaded per loop. Default: 200')
args = parser.parse_args()


class entrez:

    def __init__(self,
                 term="",
                 type="",
                 db="",
                 gene_string="",
                 Lmin="",
                 Lmax="",
                 cache = 200,
                 printing = True):

        self.type = type
        self.term = term.replace(" ", "%20")
        self.db = db
        self.cache = cache
        self.printing = printing


        if self.db == "nuccore":

            if gene_string != "" and len(gene_string.split(",")) == 1:
                gene_string = " OR ".join([i + "[All Fields]" for i in gene_string.split(",")])

            elif gene_string != "" and len(gene_string.split(",")) > 1:
                gene_string = "(" + \
                       " OR ".join([i + "[All Fields]" for i in gene_string.split(",")]) + \
                       ")"

            if Lmin != "" and Lmax != "":
                Lrange = "(" + str(Lmin) + "[SLEN] :" + str(Lmax) + "[SLEN])"
            else:
                Lrange = ""

            self.term = re.sub(" ",
                               "%20",
                               " AND ".join(
                                   [i for i in [self.term + "[Organism]", gene_string, Lrange] if i != ""]
                                    )
                               )

        self.esarch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=" + \
                          self.db + "&term=" + self.term

        self.efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db="

        self.ids = []

    def _get_ids(self):

        page = None

        while page is None:
            try:
                page = urllib.request.urlopen(self.esarch_url).read().decode('utf-8')

            except urllib.error.HTTPError:
                pass

        counts = re.sub(".*><Count>([0-9]+)</Count><.*", "\\1", page.replace("\n", ""))

        complete_esearch_url = self.esarch_url + "&retmax=" + counts

        ids_page = urllib.request.urlopen(complete_esearch_url).read().decode('utf-8')

        self.ids = [re.sub("<Id>([0-9\.]+)</Id>", "\\1", i) for i in re.findall("<Id>[0-9\.]+</Id>", ids_page)]

        return self.ids

    def get_seqs(self,
                 ids=""):

        if ids == "":
            ids = self._get_ids()

        i = 0
        if self.printing:
            while (i <= len(ids)):
                complete_efetch_url = self.efetch_url + self.db +\
                                      "&id=" + ",".join( ids[i:i + self.cache] ) +\
                                      "&rettype=" + self.type

                print(urllib.request.urlopen(complete_efetch_url).read().decode('utf-8'))
                i += self.cache
        else:
            string = ""
            while (i <= len(ids)):
                complete_efetch_url = self.efetch_url + self.db +\
                                      "&id=" + ",".join(ids[i:i + self.cache]) +\
                                      "&rettype=" + self.type

                page = urllib.request.urlopen(complete_efetch_url).read().decode('utf-8')
                string += page
                i += self.cache

            return string

    def feature_table(self, keyword):

        ids = self._get_ids()

        def GenesftByText(page, keyWords=["gene"]):

            feats = list(filter(None, page.split(">Feature ")))
            # keyWords = ["gene", "rRNA", "tRNA"]

            matchPattern = "[0-9<>\t]+%s\n[\t]+[A-Za-z]+\t.+?(?=\n)"
            subPattern = "([0-9<>]+)\t([0-9<>]+)\t%s\n[\t]+[A-Za-z]+\t(.*)"

            allFeats = []

            for ft in feats:
                # ft = feats[8]
                # keyWords = ["gene", "rRNA"]
                tmpRegions = []

                for key in keyWords:

                    tmpMatch = re.findall(matchPattern % key, ft)

                    for mtchs in tmpMatch:
                        tmpSub = re.sub(subPattern % key
                                        , "\\1,\\2,\\3,%s" % key
                                        , mtchs).replace("<", "").replace(">", "")

                        tmpRegions.append(tmpSub)

                positions = [",".join(i.split(',')[0:2]) for i in tmpRegions]

                for josp in list(set(positions)):
                    josr = [i for i in tmpRegions if re.findall(josp, i)]

                    lenOfRegionName = [len(i.split(',')[2]) for i in josr]

                    shortestWord = [x for _, x in sorted(zip(lenOfRegionName, josr))][0]

                    allFeats.append(

                        shortestWord.split(',')[2].lower()
                    )

            return dict(Counter(allFeats))

        dict1 = {}

        i = 0
        while ( i <= len(ids) ):

            complete_efetch_url = self.efetch_url +\
                                  self.db +\
                                  "&id=" +\
                                  ",".join( ids[ i:i + self.cache ] ) +\
                                  "&rettype=" +\
                                  self.type

            page = urllib.request.urlopen(complete_efetch_url).read().decode('utf-8')

            dict2 = GenesftByText(page = page,
                                  keyWords= keyword)

            dict1.update(dict2)

            i += self.cache

        return dict(
            sorted( dict1.items()
                    , key =  lambda kv: kv[1]
                    , reverse=True)
        )

if str(args.db) == "nuccore" and args.type == "ft" and args.plot == True:

    c = entrez(term=str(args.string),
               type=str(args.type),
               db=str(args.db)).feature_table( keyword = str(args.markers).split(",") )

    arr = [i for i in range(0, c.__len__()) ]

    print("Plotting...")

    plt.figure(figsize=(8, 5.5))
    plt.bar(arr
            , c.values()
            , align="center"
            , alpha=0.5)
    plt.xticks(arr
               , c.keys()
               , rotation=87)
    plt.subplots_adjust(bottom=0.33)
    plt.xlabel('Genes')
    plt.ylabel('Frequency')
    plt.title('Gene availability of %s' % str(args.string) )
    plt.axhline(y=3
                , color="black")
    plt.savefig('%s_GeneAvailability.png' % str(args.string).replace(" ","_") )
    plt.show(block = False)
    plt.close()

elif str(args.db) == "nuccore" and args.ids == False and args.plot == False:

    entrez(term=str(args.string),
           type=str(args.type),
           db=str(args.db),
           gene_string=str(args.markers),
           Lmin=str(args.Lmin),
           Lmax=str(args.Lmax),
           printing=True).get_seqs()

elif args.ids:
    for i in entrez(term=str(args.string),
                    db=str(args.db),
                    gene_string=str(args.markers),
                    Lmin=str(args.Lmin),
                    Lmax=str(args.Lmax))._get_ids():
        print(i)