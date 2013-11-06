import xmlrpclib
from Bicho.backends import Backend
from Bicho.common import Issue

# grabbing bug ID & "title" a.k.a. "summary"

# class TracIssue(Issue):


rpc_url = "https://brainwane:for-api-access@code.djangoproject.com/login/rpc"
trac = xmlrpclib.ServerProxy(rpc_url)

notclosed = trac.ticket.query("status!=closed")
chunkoftix = notclosed[60:70]

multicall = xmlrpclib.MultiCall(trac)
twr = [] # tickets with attributes
for x in chunkoftix:
    multicall.ticket.get(x)
result = multicall()

for ticket in result:
    twr.append({"id":ticket[0],
                "summary":ticket[3]["summary"]
                # "status":ticket[3]["status"],
                # "reported":ticket[1]
                })


# next: get them into the database


class TracBackend(Backend):

























Backend.register_backend("trac", Trac)
