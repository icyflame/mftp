from bs4 import BeautifulSoup as bs, CData
from os import environ as env
import re
import hashlib

import settings

from erp import tnp_login, req_args

NUM_NOTICES_DIFFED = 50

ERP_COMPANIES_URL = 'https://erp.iitkgp.ernet.in/TrainingPlacementSSO/ERPMonitoring.htm?action=fetchData&jqqueryid=37&_search=false&nd=1448725351715&rows=20&page=1&sidx=&sord=asc&totalrows=50'
ERP_NOTICEBOARD_URL = 'https://erp.iitkgp.ernet.in/TrainingPlacementSSO/Notice.jsp'
ERP_NOTICES_URL = 'https://erp.iitkgp.ernet.in/TrainingPlacementSSO/ERPMonitoring.htm?action=fetchData&jqqueryid=54&_search=false&nd=1448884994803&rows=20&page=1&sidx=&sord=asc&totalrows=50'
ERP_ATTACHMENT_URL = 'https://erp.iitkgp.ernet.in/TrainingPlacement/TPJNFDescriptionShow?filepath='
ERP_NOTICE_CONTENT_URL = 'https://erp.iitkgp.ernet.in/TrainingPlacementSSO/ShowContent.jsp?year=%s&id=%s'

@tnp_login
def check_notices(session, sessionData):
    r = session.get(ERP_NOTICEBOARD_URL, **req_args)
    r = session.get(ERP_NOTICES_URL, **req_args)
    
    print "ERP and TNP login completed!"

    notices_list = bs(r.text, 'html.parser')

    notices = []
    # Only check the first 50 notices
    for row in notices_list.find_all('row')[:NUM_NOTICES_DIFFED]:
        notice = {}

        cds = filter(lambda x: isinstance(x, CData), row.find_all(text=True))

        notice['subject'] = cds[2].string
        notice['company'] = cds[3].string

        a = bs(cds[4].string, 'html.parser').find_all('a')[0]
        m = re.search(r'ViewNotice\("(.+?)","(.+?)"\)', a.attrs['onclick'])
        year, id_ = m.group(1), m.group(2)
        content = bs(session.get(ERP_NOTICE_CONTENT_URL % (year, id_)).text, 'html.parser')
        content_div = bs.find_all(content, 'div', {'id': 'printableArea'})[0]
        notice['text'] = content_div.decode_contents(formatter='html')
        notice['time'] = cds[6].string

        a = bs(cds[7].string, 'html.parser').find_all('a')[0]
        if a.attrs['title'] == 'Download':
            onclick = a.attrs['onclick']
            m = re.search(r'TPNotice\("(.+)"\)', onclick)
            notice['attachment_url'] = ERP_ATTACHMENT_URL + m.group(1)
            r = session.get(notice['attachment_url'], stream=True)
            r.raw.decode_content = True
            hash_ = hashlib.md5()
            for chunk in iter(lambda: r.raw.read(4096), b""):
                hash_.update(chunk)
            notice['attachment_md5'] = hash_.hexdigest()

        notices.append(notice)

    print "Length of notices: %d" % len(notices)
    
    #  for i in notices[:5]:
#
        #  print i
        #  print '\n\n'

    import datetime
    soup = bs("<html><head/><body style='margin:20px'><div class='container'><h3>Last updated %s</h3><div id='content'></div></div></html>" % datetime.datetime.now(), "lxml")

    refresher = soup.new_tag("meta", content="50")
    refresher['http-equiv'] = "refresh"

    soup.select("head")[0].append(refresher)

    title1 = soup.new_tag('title')
    title1.string = "CDC Notice Board - LOCAL"

    soup.select("head")[0].append(title1)

    link1 = soup.new_tag('link', rel="stylesheet", \
            href="bootstrap.min.css")

    soup.select("head")[0].append(link1)

    div = soup.select("#content")[0]

    for i in notices:

        tag = soup.new_tag("div")

        contents = bs(i['text'], 'lxml')
        i_t = soup.new_tag("i")
        i_t.string = i['time']
        title = soup.new_tag("h3")
        title.string = "%s - %s" % (i['company'], i['subject'])
        br_t = soup.new_tag("br")
        hr_t = soup.new_tag("hr")

        orders = [title, br_t, i_t, br_t]

        for j in contents.select("body")[0].contents:
            orders.append(j)

        orders.append(br_t)

        attachment = None

        if 'attachment_url' in i.keys():
            attachment = soup.new_tag("a", href=i['attachment_url'], target="_blank")
            attachment.string = "Attachment"
            orders.append(br_t)
            orders.append(attachment)
            orders.append(br_t)
            orders.append(br_t)

        orders.append(hr_t)

        for j in orders:
            tag.append(j)

        div.append(tag)

    with open("index.html", "w") as filout:

        u = soup.prettify()
        u = u.encode("ascii", "ignore")
        filout.write(u)

if __name__ == '__main__':

    check_notices()
