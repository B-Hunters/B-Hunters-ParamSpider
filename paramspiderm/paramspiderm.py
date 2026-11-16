from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
from karton.core.resource import LocalResource
import shutil
import re
from bson.objectid import ObjectId
import requests

class paramspiderm(BHunters):
    """
    B-Hunters-ParamSpider developed by 0xBormaa
    """

    identity = "B-Hunters-ParamSpider"
    version = __version__
    persistent = True
    filters = [
        
        {
            "type": "subdomain", "stage": "new"
        }
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
                    
    def scan(self,url):        
        result=self.katanacommand(url)
        
        return result
    def katanacommand(self,url):
        result=[]

        try:
            outputfile=self.generate_random_filename()
            output = subprocess.run(["paramspider","-o",outputfile,"-d", url ], capture_output=True, text=True, timeout=900)
            data=output.stdout.split("\n")
            try:
                
                # Open the file in read mode
                if os.path.exists(outputfile):
                    with open(outputfile, "r") as file:
                        # Read the contents of the file
                        file_contents = file.read()
                        data=file_contents.split("\n")
                        result=data
                    os.remove(outputfile)
            except Exception as e:
                self.log.error(e)
                                


        except Exception as e:
            print("error ",e)
            # result=[]
        return result
    
    def process(self, task: Task) -> None:
        source=task.payload["source"]
        url = task.payload["data"]
        domain = task.payload["subdomain"]
        db=self.db
        self.scanid=task.payload_persistent["scan_id"]
        
        report_id=task.payload_persistent["report_id"]
        collection = db["domains"]
        self.scanid=task.payload_persistent["scan_id"]
        try:
                
            self.log.info("Starting processing new url")
            self.log.warning(url)
            domain = re.sub(r'^https?://', '', domain)
            domain = domain.rstrip('/')
            self.update_task_status(domain,"Started")
            result=self.scan(url)
            self.waitformongo()
            db=self.db
            collection = db["links"]
            urlstripped = re.sub(r'^https?://', '', url)
            urlstripped = urlstripped.rstrip('/')
            result = list(set(result))
            existing_document = collection.find_one({"report_id":ObjectId(report_id),"source":self.identity})
            new_links=[]
            if existing_document:
                existing_links = existing_document.get("Links", [])
                new_links = [link for link in result if link not in existing_links]
            else:
                new_links=result
            # A link that is an empty string produces an empty upload, and
            # an empty upload is not a valid task resource.  Drop them here
            # so the resource always carries something.
            new_links=[link for link in new_links if link]
            if new_links !=[] and new_links!=[url]:
                resultdata = "\n".join(map(lambda x: str(x), new_links)).encode()
                self.log.info("Uploading data of "+url)
                # The URL list is registered as a task resource instead of
                # being uploaded directly.  Karton's garbage collector drops
                # every object in the bucket that no live task references,
                # so an unregistered upload is deleted within minutes and
                # the path scanners then fail to download the list they
                # were sent.
                path_list = LocalResource(
                    name="paths",
                    content=resultdata,
                    uid="paramspider_"+self.scanid+"_"+self.encode_filename(urlstripped),
                    bucket="bhunters",
                )
                collection.update_one({"report_id": ObjectId(report_id),"source":self.identity}, {"$push": {f"Links": {"$each": new_links}}}, upsert=True)

                tag_task = Task(
                    {"type": "paths", "stage": "scan"},
                    payload={"data": urlstripped,
                            "subdomain":domain,
                    "source":"paramspider",
                    "path_list":path_list
                    }
                )
                self.send_task(tag_task)

            # Get domain_id from domain
            collection = db["domains"]
            jsdata=[]
            for i in result:
                
                if ".js" in i and i !="":
                    
                    try:
                        if is_javascript_url(i):

                            collection2 = db["js"]
                            existing_document = collection2.find_one({"report_id":ObjectId(report_id),"url": i})
                            if existing_document is None:
                                jsdata.append(i)
                                tag_task = Task(
                                    {"type": "js", "stage": "new"},
                                    payload={"data": url,
                                    "subdomain":domain,
                                    "file": i,
                                    "module":"katana"
                                    }
                                )
                                self.send_task(tag_task)
                    except Exception as e:
                        raise Exception(e)
    
            self.update_task_status(domain,"Finished")

        except Exception as e:
            self.update_task_status(domain,"Failed")
            raise Exception(e)


#: The media types a server may use for a JavaScript file.  The
#: ``application/javascript`` type was never registered and RFC 9239
#: obsoleted it in favour of ``text/javascript``; Flask, Werkzeug and most
#: modern servers send the latter.  The shared base class in the published
#: ``b-hunters`` package still only accepts the old type, so the check is
#: repeated here until a release of the package carries the fix.
JS_CONTENT_TYPES = (
    "application/javascript",
    "text/javascript",
    "application/x-javascript",
    "application/ecmascript",
    "text/ecmascript",
)


def is_javascript_url(url):
    """Is the URL served as JavaScript?"""
    try:
        response = requests.get(url, timeout=10)
    except Exception:
        return False
    media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    return media_type in JS_CONTENT_TYPES
