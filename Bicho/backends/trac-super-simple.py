import xmlrpclib
import sys
from Bicho.backends import Backend
from Bicho.common import Issue
from Bicho.utils import printdbg, printerr, printout
from Bicho.db.database import DBBackend

# grabbing bug ID & "title" a.k.a. "summary"

rpc_url = "https://brainwane:for-api-access@code.djangoproject.com/login/rpc"
trac = xmlrpclib.ServerProxy(rpc_url)
notclosed = trac.ticket.query("status!=closed")
chunkoftix = notclosed[60:70]

multicall = xmlrpclib.MultiCall(trac)

class TracBackend(Backend):

    def analyze_bug(self, bug):
        """Take each bug in the collection returned by the API call and append each bug attribute onto a unique Issue object."""
        printdbg("analyzing a new bug")
        bugid = bug[0]
        bugsummary = bug[3]['summary']
        issue = Issue(bugid, None, bugsummary, None, None, None)
        return issue

    def run(self):       
        print("Running Bicho")

        bugsdb = get_database(DBBackend())
        printdbg(rpc_url)

        for x in chunkoftix:
            multicall.ticket.get(x)
        bugs = multicall()

        bugsdb.insert_supported_traker("trac", "x.x")
        trk = Tracker(rpc_url, "trac", "x.x")
        dbtrk = bugsdb.insert_tracker(trk)

        nbugs = len(bugs)
        if nbugs == 0:
            printout("No bugs found. Did you provide the correct URL?")
            sys.exit(0)

        analyzed = []

        for bug in bugs:
            try:
                issue_data = self.analyze_bug(bug)
            except Exception:
                printerr("Error in function analyze_bug with Bug: %s" % bug[0])
                raise

            try:
                bugsdb.insert_issue(issue_data, dbtrk.id)
            except UnicodeEncodeError:
                printerr("UnicodeEncodeError: the issue %s couldn't be stored"
                      % (issue_data.issue))
            except NotFoundError:
                printerr("NotFoundError: the issue %s couldn't be stored"
                         % (issue_data.issue))
            except Exception, e:
                printerr("Unexpected Error: the issue %s couldn't be stored"
                         % (issue_data.issue))
                print e
            

        try:
            # we read the temporary table with the relationships and create
            # the final one
            bugsdb.store_final_relationships()
        except:
            raise

        printout("Done. %s bugs analyzed" % (nbugs))

Backend.register_backend("trac", Backend)
