# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013 GSyC/LibreSoft, Universidad Rey Juan Carlos,
# Sumana Harihareswara
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Authors: Sumana Harihareswara <sumanah@panix.com>

import xmlrpclib

import datetime
import time
import sys

from storm.locals import Int, DateTime, Unicode, Reference, Desc

from dateutil.parser import parse
from Bicho.common import Issue, People, Tracker, Comment, Change, Attachment
from Bicho.backends import Backend
from Bicho.db.database import DBIssue, DBBackend, DBTracker, get_database
from Bicho.Config import Config
from Bicho.utils import printout, printerr, printdbg
from BeautifulSoup import BeautifulSoup, Tag, NavigableString 
#from BeautifulSoup import NavigableString
from BeautifulSoup import Comment as BFComment
#from Bicho.Config import Config
#from Bicho.utils import *

import xml.sax.handler
#from xml.sax._exceptions import SAXParseException

import feedparser



class DBTracIssueExt(object):
    """
    """
    __storm_table__ = 'issues_ext_trac'

    id = Int(primary=True)
    issue_key = Unicode()
    link = Unicode()
    title = Unicode()
    status = Unicode()
    resolution = Unicode()

    issue_id = Int()

    issue = Reference(issue_id, DBIssue.id)

    def __init__(self, issue_id):
        self.issue_id = issue_id


class DBTracIssueExtMySQL(DBTracIssueExt):
    """
    MySQL subclass of L{DBTracIssueExt}
    """

    __sql_table__ = 'CREATE TABLE IF NOT EXISTS issues_ext_trac ( \
                     id INTEGER NOT NULL AUTO_INCREMENT, \
                     issue_key VARCHAR(32) NOT NULL, \
                     link VARCHAR(100) NOT NULL, \
                     title VARCHAR(100) NOT NULL, \
                     version VARCHAR(35) NOT NULL, \
                     status  VARCHAR(35) NOT NULL, \
                     resolution VARCHAR(35) NOT NULL, \
                     issue_id INTEGER NOT NULL, \
                     PRIMARY KEY(id), \
                     UNIQUE KEY(issue_id), \
                     INDEX ext_issue_idx(issue_id), \
                     FOREIGN KEY(issue_id) \
                       REFERENCES issues (id) \
                         ON DELETE CASCADE \
                         ON UPDATE CASCADE \
                     ) ENGINE=MYISAM;'


class DBTracBackend(DBBackend):
    """
    Adapter for Trac backend.
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
        
        newIssue = False;

        try:
            db_issue_ext = store.find(DBTracIssueExt,
                                    DBTracIssueExt.issue_id == issue_id).one()
            if not db_issue_ext:
                newIssue = True
                db_issue_ext = DBTracIssueExt(issue_id)
            
            db_issue_ext.title = self.__return_unicode(issue.title)
            db_issue_ext.issue_key = self.__return_unicode(issue.issue_key)
            db_issue_ext.link = self.__return_unicode(issue.link)
            db_issue_ext.status = self.__return_unicode(issue.status)
            db_issue_ext.resolution = self.__return_unicode(issue.resolution)

            if newIssue == True:
                store.add(db_issue_ext)

            store.flush()
            return db_issue_ext
        except:
            store.rollback()
            raise

    def __return_unicode(self, str):
        """
        Decodes string and pays attention to empty ones
        """
        if str:
            return unicode(str)
        else:
            return unicode('')

####################################

class TracIssue(Issue):
    """
    Ad-hoc Issue extensions for Trac's issue
    """
    def __init__(self,issue, type, summary, description, submitted_by, submitted_on):
        Issue.__init__(self,issue, type, summary, description, submitted_by, submitted_on)
        
        self.title = None
        self.issue_key = None
        self.link = None
        self.status = None
        self.resolution = None

    def setStatus(self, status):
        self.status = status

    def setResolution(self, resolution):
        self.resolution = resolution

    def setTitle(self, title): 
        self.title = title

    def setIssue_key(self, issue_key):
        self.issue_key = issue_key

    def setLink(self, link):
        self.link = link

class Bug():
    
    def __init__ (self):
        self.title = None
        self.link = None
        self.description = ""
        self.summary = None
        self.status = None
        self.resolution = None
        self.created = None
        self.updated = None
        self.issue_key = None
        self.key_id = None
        
class BugsHandler(xml.sax.handler.ContentHandler):

    def __init__ (self):
        self.issues_data = []
        self.init_bug()

    def init_bug (self):

        self.mapping = []
        self.comments = []

        self.title = None
        self.link = None
        self.description = ""
        self.summary = None
        self.status = None
        self.resolution = None
        self.created = None
        self.updated = None
        self.issue_key = None
        self.key_id = None

        #control data
        self.first_desc = True
        self.is_title = False
        self.is_link = False
        self.is_description = False
        self.is_environment = False
        self.is_summary = False
        self.is_bug_type = False
        self.is_status = False
        self.is_resolution = False
        self.is_security = False
        self.is_created = False
        self.is_updated = False
        self.is_version = False
        self.is_component = False
        self.is_votes = False

        self.is_project = False
        self.is_issue_key = False
        self.is_assignee = False
        self.is_reporter = False
        self.is_comment = False
        self.is_customfieldname = False
        self.is_customfieldvalue = False

    def startElement(self, name, attrs):
        if name == "item":
            self.init_bug()
        elif name == 'title':
            self.is_title = True
        elif name == 'link':
            self.is_link = True
            self.link = ''
        elif name == 'description':
            self.is_description = True
        elif name == 'summary':
            self.is_summary = True
        elif name == 'status':
            self.is_status = True
        elif name == 'resolution':
            self.is_resolution = True
        elif name == 'security':
            self.is_security = True
        elif name == 'created':
            self.is_created = True
            self.created = ''
        elif name == 'updated':
            self.is_updated = True
            self.updated = ''
        elif name == 'key':
            self.is_issue_key = True
            self.key_id = attrs['id']


    def characters(self, ch):
        if self.is_title:
            self.title = ch
        elif self.is_link:
            self.link += ch
        elif self.is_description:
            #FIXME problems with ascii, not support str() function
            if (self.first_desc == True):
                self.first_desc = False
            else:
                self.description = self.description + ch.strip()
        elif self.is_summary:
            self.summary = ch
        elif self.is_status:
            self.status = ch
        elif self.is_resolution:
            self.resolution = ch
        elif self.is_created:
            self.created += ch
        elif self.is_updated:
            self.updated += ch
        elif self.is_issue_key:
            self.issue_key = ch

    def endElement(self, name):
        if name == 'title':
            self.is_title = False
        elif name == 'link':
            self.is_link = False
        elif name == 'description':
            self.is_description = False
        elif name == 'key':
            self.is_issue_key = False
        elif name == 'summary':
            self.is_summary = False
        elif name == 'status':
            self.is_status = False
        elif name == 'resolution':
            self.is_resolution = False
        elif name == 'created':
            self.is_created = False
        elif name == 'updated':
            self.is_updated = False
         
        elif name == 'item':
            newbug = Bug()
            newbug.title = self.title
            newbug.link = self.link
            newbug.description = self.description
            newbug.summary = self.summary
            newbug.status = self.status
            newbug.resolution = self.resolution
            newbug.created = self.created
            newbug.updated = self.updated
            newbug.version = self.version
            newbug.issue_key = self.issue_key
            newbug.key_id = self.key_id

            self.issues_data.append(newbug)

    @staticmethod
    def remove_unicode(str):
        """
        Cleanup u'' chars indicating a unicode string
        """
        if (str.startswith('u\'') and str.endswith('\'')):
            str = str[2:len(str) - 1]
        return str

    def getIssues(self):
        bicho_bugs = []
        for bug in self.issues_data:
            bicho_bugs.append(self.getIssue(bug))
        return bicho_bugs
        
    def getIssue(self, bug):
        #Return the parse data bug into issue object
        issue_id = bug.key_id
        issue_type = bug.bug_type
        summary = bug.summary
        description = bug.description
        status = bug.status
        resolution = bug.resolution

        assigned_by = People(bug.assignee_username)
        assigned_by.set_name(bug.assignee)
        assigned_by.set_email(BugsHandler.getUserEmail(bug.assignee_username))

        submitted_by = People(bug.reporter_username)
        submitted_by.set_name(bug.reporter)
        submitted_by.set_email(BugsHandler.getUserEmail(bug.reporter_username))

        submitted_on = parse(bug.created).replace(tzinfo=None)

        issue = TracIssue(issue_id, issue_type, summary, description, submitted_by, submitted_on)
        issue.setIssue_key(bug.issue_key)
        issue.setTitle(bug.title)
        issue.setLink(bug.link)
        issue.setUpdated(parse(bug.updated).replace(tzinfo=None))
        issue.setStatus(status)
        issue.setResolution(resolution)

        bug_activity_url = bug.link + '?page=com.atlassian.jira.plugin.system.issuetabpanels%3Achangehistory-tabpanel' # gotta fix!!!
        printdbg("Bug activity: " + bug_activity_url)
        data_activity = urllib.urlopen(bug_activity_url).read()
        parser = SoupHtmlParser(data_activity, bug.key_id)
        changes = parser.parse_changes()
        for c in changes:
            issue.add_change(c)

        return issue

class TracBackend(Backend):
    """
    Trac Backend
    """

    def __init__(self):
        self.delay = Config.delay
        self.url = Config.url
        
    def basic_trac_url(self):
        serverUrl = self.url.split("/browse/")[0]
        product = self.url.split("/browse/")[1]
        query = "/sr/jira.issueviews:searchrequest-xml/temp/SearchRequest.xml" # gotta fix!!!
        url_issues = serverUrl + query + "?pid=" + product
        url_issues += "&sorter/field=updated&sorter/order=INC"
        if self.last_mod_date:
             url_issues += "&updated:after=" + self.last_mod_date
        return url_issues

    def bugsNumber(self,url):
        oneBug = self.basic_trac_url()
        oneBug += "&tempMax=1"
        printdbg("Getting number of issues: " + oneBug)
        data_url = urllib.urlopen(oneBug).read()
        bugs = data_url.split("<issue")[1].split('\"/>')[0].split("total=\"")[1]
        return int(bugs)

    # http://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python
    def valid_XML_char_ordinal(self, i):
        return ( # conditions ordered by presumed frequency
            0x20 <= i <= 0xD7FF
            or i in (0x9, 0xA, 0xD)
            or 0xE000 <= i <= 0xFFFD
            or 0x10000 <= i <= 0x10FFFF
            )
        
    def safe_xml_parse(self, url_issues, handler):
        f = urllib.urlopen(url_issues)
        parser = xml.sax.make_parser()
        parser.setContentHandler(handler)

        try:
            contents = f.read()
            parser.feed(contents)
            parser.close()
        except Exception:
            # Clean only the invalid XML
            try:
                parser2 = xml.sax.make_parser()
                parser2.setContentHandler(handler)
                parser2.setContentHandler(handler)
                printdbg("Cleaning dirty XML")
                cleaned_contents = ''. \
                    join(c for c in contents if self.valid_XML_char_ordinal(ord(c)))
                parser2.feed(cleaned_contents)
                parser2.close()
            except Exception:
                printerr("Error parsing URL: %s" % (url_issues))
                raise
        f.close()

    def analyze_bug_list(self, nissues, offset, bugsdb, dbtrk_id):
        url_issues = self.basic_trac_url()
        url_issues += "&tempMax=" + str(nissues) + "&pager/start=" + str(offset)
        printdbg(url_issues)
        
        handler = BugsHandler()
        self.safe_xml_parse(url_issues, handler)

        try:
            issues = handler.getIssues()            
            for issue in issues:
                bugsdb.insert_issue(issue, dbtrk_id)
        except Exception, e:
            import traceback
            traceback.print_exc()
            sys.exit(0)
 
    def run(self):
        printout("Running Bicho with delay of %s seconds" % (str(self.delay)))

        issues_per_xml_query = 500
        bugsdb = get_database(DBTracBackend())

        bugsdb.insert_supported_traker("trac","1.0.0")
        trk = Tracker(self.url.split("-")[0], "trac", "1.0.0")
        dbtrk = bugsdb.insert_tracker(trk)

        serverUrl = self.url.split("/browse/")[0]
        query = "/si/jira.issueviews:issue-xml/" # gotta fix!!!
        project = self.url.split("/browse/")[1]

        if (project.split("-").__len__() > 1):
            bug_key = project
            project = project.split("-")[0]
            bugs_number = 1

            printdbg(serverUrl + query + bug_key + "/" + bug_key + ".xml")

            parser = xml.sax.make_parser(  )
            handler = BugsHandler(  )
            parser.setContentHandler(handler)
            try:
                parser.parse(serverUrl + query + bug_key + "/" + bug_key + ".xml")
                issue = handler.getIssues()[0]
                bugsdb.insert_issue(issue, dbtrk.id)
            except Exception, e:
                #printerr(e)
                print(e)

        else:
            self.last_mod_date = bugsdb.get_last_modification_date(dbtrk.id)
            if self.last_mod_date:
                # self.url = self.url + "&updated:after=" + last_mod_date
                printdbg("Last bugs cached were modified at: %s" % self.last_mod_date)

            bugs_number = self.bugsNumber(self.url)
            print "Tickets to be retrieved:", str(bugs_number)
            remaining = bugs_number
            while (remaining > 0):
                self.analyze_bug_list(issues_per_xml_query, bugs_number - remaining, bugsdb, dbtrk.id)
                remaining -= issues_per_xml_query
                #print "Remaining time: ", (remaining/issues_per_xml_query)*Config.delay/60, "m", "(",remaining,")"
                time.sleep(self.delay)

            printout("Done. %s bugs analyzed" % (bugs_number))

Backend.register_backend("trac", TracBackend)
