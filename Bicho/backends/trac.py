import xmlrpclib
import sys
import datetime
from Bicho.backends import Backend
from Bicho.common import Issue, Tracker, People
from Bicho.utils import printdbg, printerr, printout
from Bicho.db.database import DBIssue, DBBackend, get_database, NotFoundError
from storm.locals import Int, Reference

# grabbing bug ID & "title" a.k.a. "summary"

rpc_url = "https://brainwane:for-api-access@code.djangoproject.com/login/rpc"
trac = xmlrpclib.ServerProxy(rpc_url)
notclosed = trac.ticket.query("status!=closed")
chunkoftix = notclosed[60:70]

multicall = xmlrpclib.MultiCall(trac)

class DBTracIssueExt(object):
    """
    Types for each field.
    """
    __storm_table__ = 'issues_ext_trac'

    id = Int(primary=True)
    issue_id = Int()
    issue = Reference(issue_id, DBIssue.id)

    def __init__(self, issue_id):
        self.issue_id = issue_id

class DBTracIssueExtMySQL(DBTracIssueExt):
    """
    MySQL subclass of L{DBTracIssueExt}
    """
    __sql_table__ = 'CREATE TABLE IF NOT EXISTS issues_ext_trac (\
                     id INTEGER NOT NULL AUTO_INCREMENT, \
                     issue_id INTEGER NOT NULL, \
                     PRIMARY KEY(id), \
                     UNIQUE KEY(issue_id), \
                     INDEX ext_issue_idx(issue_id), \
                     FOREIGN KEY(issue_id) \
                       REFERENCES issues(id) \
                         ON DELETE CASCADE \
                         ON UPDATE CASCADE \
                     ) ENGINE=MYISAM; '

class DBTracBackend(DBBackend):
    """
    Adapter for Trac backend, to make it so there is a MYSQL_EXT.
    """
    def __init__(self):
        self.MYSQL_EXT = [DBTracIssueExtMySQL]

    def insert_issue_ext(self, store, issue, issue_id):
        """
        Insert the given extra parameters of issue with id X{issue_id}.

        @param store: database connection
        @type store: L{storm.locals.Store}
        @param issue: issue to insert
        @type issue: L{TracIssue}
        @param issue_id: identifier of the issue
        @type issue_id: C{int}

        @return: the inserted extra parameters issue
        @rtype: L{DBTracIssueExt}
        """

        newIssue = False

        try:
            db_issue_ext = store.find(DBTracIssueExt,
                                      DBTracIssueExt.issue_id
                                      ==
                                      issue_id).one()
            if not db_issue_ext:
                newIssue = True
                db_issue_ext = DBTracIssueExt(issue_id)

            if newIssue == True:
                store.add(db_issue_ext)

            store.flush()
            return db_issue_ext
        except:
            store.rollback()
            raise

class TracBackend(Backend):

    def analyze_bug(self, bug):
        """Take each bug in the collection returned by the API call and append each bug attribute onto a unique Issue object."""
        printdbg("analyzing a new bug")
        bugid = bug[0][0]
        bugsummary = bug[0][3]['summary']
        issue = Issue(bugid, None, bugsummary, None, People(1), datetime.datetime.today())
        return issue

    def run(self):       
        print("Running Bicho")

        bugsdb = get_database(DBTracBackend())
        printdbg(rpc_url)

        for x in chunkoftix:
            multicall.ticket.get(x)
        bugs = multicall()

        bugsdb.insert_supported_traker("trac", "x.x")
        trk = Tracker(rpc_url, "trac", "x.x")
        dbtrk = bugsdb.insert_tracker(trk)

        nbugs = len(bugs.results)
        if nbugs == 0:
            printout("No bugs found. Did you provide the correct URL?")
            sys.exit(0)

        analyzed = []

        for bug in bugs.results:
            try:
                issue_data = self.analyze_bug(bug)
                printout("Analyzing bug # %s" % bug[0][0])
            except Exception:
                printerr("Error in function analyze_bug with Bug: %s" % bug[0])
                raise

            bugsdb.insert_issue(issue_data, dbtrk.id)
            # except UnicodeEncodeError:
            #     printerr("UnicodeEncodeError: the issue %s couldn't be stored"
            #           % (issue_data.issue))
            # except NotFoundError:
            #     printerr("NotFoundError: the issue %s couldn't be stored"
            #              % (issue_data.issue))
            # except Exception, e:
            #     printerr("Unexpected Error: the issue %s couldn't be stored"
            #              % (issue_data.issue))
            #     print e
            

        try:
            # we read the temporary table with the relationships and create
            # the final one
            bugsdb.store_final_relationships()
        except:
            raise

        printout("Done. %s bugs analyzed" % (nbugs))

Backend.register_backend("trac", TracBackend)
