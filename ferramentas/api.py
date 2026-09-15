import urllib.request, json, urllib.parse, time
BASE="https://api.mosiaomnichannel.com.br/publico/omni/rede_credenciada/v1/gan/"
H={"Content-Type":"application/json","instancia_aplicacao":"2","bundle":"br.com.mobilesaude.paranaclinicas",
   "Origin":"https://funcionalidades-front.mosiaomnichannel.com.br","Referer":"https://funcionalidades-front.mosiaomnichannel.com.br/","User-Agent":"Mozilla/5.0"}
def call(path, payload, tries=3):
    data=json.dumps(payload).encode()
    for i in range(tries):
        req=urllib.request.Request(BASE+path, data=data, headers=H, method="POST")
        try:
            r=urllib.request.urlopen(req, timeout=60)
            return json.loads(r.read().decode('utf-8','replace'))
        except Exception as e:
            body=e.read().decode('utf-8','replace') if hasattr(e,'read') else ''
            if i==tries-1: return {"_err":str(e),"_body":body}
            time.sleep(2)
