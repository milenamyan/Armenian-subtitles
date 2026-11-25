# HaySub․ սովորենք մեկ ենթագրի ճանապարհով

Բացում ես ֆիլմերի ցանկը, ընտրում «22 Փամփուշտ»-ը և սեղմում **Play**։ Ինչպե՞ս է ճիշտ նախադասությունը հայտնվում հենց խոսքի պահին։ Նախ պետք է գտնել ֆիլմը, հետո՝ նրա ենթագրերի ֆայլը, իսկ դիտելիս՝ համեմատել ենթագրի երկու ժամերը տեսանյութի ընթացիկ ժամանակի հետ։ Եթե ենթագիրն արդեն հայերեն է, այս ճանապարհին թարգմանչի կարիք չկա։ Եթե դեռ միայն բնագիրն ունես, կարող ես նախ պատրաստել հայերեն ֆայլը HaySub-ի տեղական ծրագրում։

Այս դասընթացը գրված է նախագծի `31cc353` տարբերակի համար։ Սկսիր դիտողի պատրաստի արդյունքից։ Հետո անցիր հեղինակի կողմը և նույն արդյունքը կառուցիր փոքր քայլերով։ Գլուխները կարելի է անցնել առանձին օրերի ընթացքում։

## Բովանդակություն

1. [Առաջին ֆիլմը․ ո՞ր ծրագիրն ես բացում](#start-here)
2. [Գործարկում․ հրամանից մինչև առաջին էջը](#run)
3. [Նախագծի քարտեզը և կարդալու հերթը](#map)
4. [Դիտողի ճանապարհը․ ցանկից մինչև էկրանի տողը](#playback) · [Python հավելվածի դիտման էջը](#server-player)
5. [Որտեղի՞ց են գալիս ենթագրերն ու դրանց ժամանակները](#subtitles)
6. [Ինչպե՞ս է թարգմանությունը շարունակվում և պահպանվում](#translation)
7. [Chrome հավելումը․ նույն ենթագիրը ուրիշ կայքի տեսանյութի վրա](#extension)
8. [Ինչպե՞ս է ֆիլմը հայտնվում տեսադարանում](#media)
9. [Ինչպե՞ս է տեսադարանը հասնում դիտողին](#publish)
10. [Ինքնուրույն աշխատանքի հերթականությունը և «Որտե՞ղ փոխել ինչ»](#roadmap)

<a id="start-here"></a>

## 1. Առաջին ֆիլմը․ ո՞ր ծրագիրն ես բացում

`browser`-ը՝ օրինակ Chrome-ը, ծրագիր է, որը ստանում ու ցուցադրում է էջերը։ `server`-ը ծրագիր է, որն ընդունում է հարցումը և վերադարձնում էջ, ֆայլ կամ տվյալներ։ Երկուսն էլ կարող են աշխատել քո համակարգչում։ Երբ դիտողը գրում է `URL`՝ ռեսուրսի հասցեն, `browser`-ը գիտի, թե ումից ինչ պահանջի։ HaySub-ում տեսանյութը, ենթագրերը և հենց էջը կարող են ունենալ երեք տարբեր հասցե։

Ահա նույն նախագծի երեք մուտքերը․ ընտրիր այն, որը համապատասխանում է քո անելիքին։

| Ինչ ես ուզում անել | Որտեղից սկսես | Առաջին տեսանելի արդյունքը |
|---|---|---|
| Ընտրել պատրաստի ֆիլմ | `catalog-site/index.html` էջը՝ հաջորդ գլխի տեղական հասցեով | Որոնման դաշտ և ֆիլմերի քարտեր։ Ընտրված քարտը բացում է `watch.html?id=…`։ |
| Թարգմանել ֆայլ կամ տնօրինել տեսադարանը | Տեղական Python հավելվածի `/` կամ `/admin` էջը | Ենթագրի ընտրություն, թարգմանությունների պատմություն, տեսադարան։ Նույն հավելվածի դիտողի ցանկը `/catalog` է։ |
| Հայերեն տող տեսնել YouTube-ի կամ այլ կայքի տեսանյութի վրա | `extension/`՝ Chrome-ի լրացուցիչ ծրագիրը | Բացում ես հավելման փոքր պատուհանը, ընտրում պատրաստի ենթագիրը կամ տեղական տարբերակում պատվիրում թարգմանություն։ |

**Ամենափոքր աշխատող կապը** ֆիլմի մեկ գրառումից մեկ հղում ստանալն է։ `JSON`-ը տվյալները անուն–արժեք զույգերով գրելու ձև է։ `id`-ն գրառման տարբերակիչն է․ նույնիսկ եթե ցուցադրվող վերնագիրը փոխվի, էջը կարող է նույն ֆիլմը գտնել դրա միջոցով։

`catalog-site/catalog.json:52–54` · `ֆիլմի գրառում`

```json
      "id": "0e2e2128cc254b83a3fc8f6ab18ab791",
      "title": "22 Փամփուշտ",
      "published": true,
```

`card(item)`-ը `function` է՝ անվանված քայլ, որին տվյալ ես տալիս։ Այստեղ `item`-ը ֆիլմի գրառումն է։ `JavaScript`-ը հենց `browser`-ում կատարվող ծրագրի լեզուն է։ Ստորև այն ստեղծում է հղում, վերնագիրն ու հասցեն վերցնում տվյալներից։

`catalog-site/catalog.js:7–8` · `card`

```javascript
  function card(item){
    const link=element('a',undefined,'movie-card');link.href='watch.html?id='+encodeURIComponent(item.id);link.title=item.title;
```

Այս ֆիլմի համար արդյունքը `watch.html?id=0e2e2128cc254b83a3fc8f6ab18ab791` է։ `?id=`-ից հետո գրված արժեքը դիտման էջին ասում է, թե ցանկից որ ֆիլմը բեռնի։ Սա առաջին ընթերցման եղանակն է․ մեկ արժեք ընտրիր և տես, թե որ տողում է այն փոխում իր դերը՝ գրառումից դառնում է հասցե։

**Արժե առանձին ուսումնասիրել — `URL query parameters`։** Երբ մի էջը կարող է բացել բազմաթիվ ֆիլմեր, հասցեով փոխանցվող արժեքը բացատրում է, թե դրանցից որն է ընտրված։ Վերադարձիր `catalog-site/catalog.js`-ի `card`-ին։

**Փորձիր ինքդ։** Բացիր `catalog-site/catalog.json`-ը, գտիր «Եղբայրներ»-ի `id`-ն և ձեռքով կազմիր դիտման հասցեի վերջը։ Պետք է ստանաս `watch.html?id=a54ade7bced54ee8883339c1fbbd7606`։ Հաջորդ գլխից հետո կարող ես այն բացել։

<a id="run"></a>

## 2. Գործարկում․ հրամանից մինչև առաջին էջը

### Նախ դիտիր արդեն պատրաստի ցանկը

Ստորև հրամանները Windows-ի **PowerShell**-ի համար են․ սա այն պատուհանն է, որտեղ հրաման ես մուտքագրում ու տեսնում արդյունքը։ **Աշխատանքային պանակ** նշանակում է այն պանակը, որի նկատմամբ հաշվում են կարճ ուղիները։ Դասընթացի **բոլոր հրամանների** աշխատանքային պանակը նախագծի արմատն է, բացառությամբ առաջին `Set-Location`-ի, որը կարելի է տալ ցանկացած պանակից։ Նոր պատուհանում կրկնիր այդ առաջին հրամանը։

```powershell
Set-Location -LiteralPath 'C:\Users\Milena Mehrabyan\Desktop\Armenian-subtitles'
Get-Location
```

Առաջինը փոխում է պանակը, երկրորդը տպում է այն։ Ճիշտ արդյունքն ավարտվում է `Desktop\Armenian-subtitles`-ով։

```powershell
py -3 -m http.server 8080 --bind 127.0.0.1 --directory catalog-site
```

`Python`-ը կոդ կատարող ծրագիրն ու այդ կոդի լեզուն է։ `-m http.server`-ը գործարկում է Python-ի պատրաստի ֆայլ մատուցող ծրագիրը։ `--directory`-ն ասում է, թե որտեղից վերցնի էջերը։ `127.0.0.1`-ը քո իսկ համակարգիչն է, `port`-ը՝ տվյալ հասցեում աշխատող ծրագիր ընտրելու համարը, այս դեպքում՝ `8080`։ Սպասիր `Serving HTTP on 127.0.0.1 port 8080` հաղորդագրությանը, ապա բացիր [տեղական ֆիլմերի ցանկը](http://127.0.0.1:8080/)։ Այս տարբերակի գրանցված ցանկում հինգ ֆիլմ կա։ Ֆիլմի պատկերը և ենթագրերը բեռնելու համար կարևոր է ցանկում նշված արտաքին հասցեների հասանելիությունը։ Ցանկի էջը դիտելու համար բավարար են Python-ը և նախագծի ֆայլերը։ Դադարեցնելու համար նույն պատուհանում սեղմիր `Ctrl+C`։

### Ապա բացիր այն ծրագիրը, որով պատրաստում ես նյութը

Նախագծի նկարագրությունը նախատեսում է Python 3.11 կամ ավելի նոր տարբերակ։ Այս օրինակում առկա `.venv`-ի Python-ը 3.13 է։ `virtual environment`-ը նախագծի առանձին Python միջավայրն է, իսկ `dependency`-ն՝ ուրիշի գրած փաթեթ, որն օգտագործում է ծրագիրը։ Օրինակ՝ `FastAPI`-ն Python-ի փաթեթն է, որը հասցեն կապում է պատասխան պատրաստող կոդին։ Սույն օրինակում արդեն կան `.venv` և `.env`։ Եթե աշխատում ես նույն պատրաստված պանակում, անմիջապես ստուգիր տարբերակը։ Եթե սկսում ես նոր պատճենից, հետևիր աղյուսակին՝ վերևից ներքև։

| Նախագծի արմատում տրվող հրամանը | Ինչ է անում | Ինչ ես ակնկալում |
|---|---|---|
| `py -3 --version` | Ստուգում է Windows-ի Python-ի հասանելի տարբերակը | `Python 3.…` և տարբերակի համարը։ |
| `if (!(Test-Path '.\.venv\Scripts\python.exe')) { py -3 -m venv .venv }` | Անհրաժեշտության դեպքում ստեղծում է միջավայրը | `.venv\Scripts\python.exe` ֆայլը գոյություն ունի։ |
| `.\.venv\Scripts\python.exe --version` | Գործարկում է հենց այս պանակի Python-ը | Միջավայրի տարբերակը։ |
| `.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt` | Նոր միջավայրում `pip` տեղադրիչով բերում է ֆայլում ամրագրված փաթեթների տարբերակները | Հաջող տեղադրում կամ `Requirement already satisfied` արդեն տեղադրվածների համար։ |
| `if (!(Test-Path '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }` | Եթե կազմաձևման ֆայլը բացակայում է, ստեղծում է այն օրինակից | Արմատում կա `.env`։ Գոյություն ունեցող անձնական կարգավորումներն օգտագործվում են ինչպես կան։ |
| `.\.venv\Scripts\python.exe -m pip check` | Ստուգում է, որ փաթեթների պահանջները համատեղելի են | Համահունչ միջավայրում՝ `No broken requirements found.`։ |

`.env`-ում յուրաքանչյուր `NAME=value` զույգ ծրագրին մի կարգավորում է տալիս։ Պատրաստի ցանկը և տեղական առաջին էջը կարելի է բացել առանց թարգմանության բանալու։ **Նոր թարգմանության համար** `API`-ն երկու ծրագրերի հաղորդակցման պայմանագիրն է, իսկ `API key`-ը ծառայությանը քո հարցումը ճանաչելու գաղտնի արժեքն է։ `.env`-ի `GEMINI_API_KEY`-ում դիր քո բանալին։ Արմատից `.\.venv\Scripts\python.exe list_models.py` հրամանը հարցնում է Google-ին և հաջողության դեպքում տպում հասանելի մոդելների անունները։ Դրանցից մեկի անունը գրիր `GEMINI_MODEL`-ում։ Այստեղ `model`-ը թարգմանության համար ընտրված լեզվային ծրագիրն է։

`list_models.py:8–11` · `մոդելների ցանկը`

```python
with genai.Client(api_key=os.environ['GEMINI_API_KEY']) as client:
    for model in client.models.list():
        if 'generateContent' in (model.supported_actions or []):
            print(model.name)
```

Եթե նոր պատճենի դատարկ տեսադարանից ես սկսում, առաջին դասի համար պահպանիր պատրաստի ֆիլմերի ցուցակը՝ այս պատուհանում տալով `$env:HAYSUB_STATIC_CATALOG_SYNC = '0'`։ Հրամանը լուռ է աշխատում։ Պատճառն այն է, որ օրինակի `.env.example`-ի 15-րդ տողը միացնում է տեղական ցուցակի արտահանումը․ դատարկ տեսադարանից կարող է գրվել դատարկ `catalog.json`։ Քո արդեն կարգավորված տեսադարանից աշխատելիս ընտրիր դրա սովորական կարգավորումը։ Այս անջատիչը և հրապարակումը նորից կհանդիպեն վերջին գլուխներում։

Տեղական ռեժիմի (`HAYSUB_PUBLIC=0`) և սովորական `8000` համարի դեպքում գործարկիր․

```powershell
.\.venv\Scripts\python.exe start.py
```

Նոր գործարկման դեպքում սպասիր `Application startup complete.` և `Uvicorn running on http://127.0.0.1:8000` հաղորդագրություններին։ Պատուհանը բաց պահիր և ինքդ բացիր [տեղական աշխատանքային էջը](http://127.0.0.1:8000/)։ Կտեսնես «Թարգմանիր SRT/VTT ենթագրերը հայերեն» վերնագիրը։ `SRT`-ն և `WebVTT`-ն (`.vtt`) ենթագրի տեքստային ֆայլերի երկու ձևաչափ են․ երկուսն էլ պահում են տվյալ տողի սկիզբը, ավարտը և բառերը։ Տեղական `/catalog` հասցեն ցույց է տալիս այս հավելվածի տեսադարանը, որը թարմ տեղադրման ժամանակ կարող է դատարկ լինել։ Այն անկախ է `8080`-ով դիտած պատրաստի ցուցակից։ Արմատում գտնվող `Start HaySub.bat`-ը կրկնակի սեղմելով էլ է գործարկվում նույն `start.py`-ն։ Կարգավորումները փոխելուց հետո սկզբնական պատուհանում սեղմիր `Ctrl+C` և նորից գործարկիր։

### Հետևիր առաջին կանչին

**1. Python-ը կարդում է ֆայլը վերևից ներքև։** `start.py`-ի 1-ին տողը մոդուլի նկարագրությունն է, 2-րդում առաջին `import`-ն է․ այն հասանելի է դարձնում այլ կոդ։ 11-րդ տողի `def main()`-ը սահմանում է քայլերը։ Ֆայլն ուղղակի գործարկելիս հենց վերջին երկու տողերն են կանչում այդ քայլերը։

`start.py:41–42` · `գործարկման մուտքը`

```python
if __name__ == '__main__':
    sys.exit(main())
```

`start.py:12–18` · `main`

```python
    root=Path(__file__).resolve().parent
    os.chdir(root)
    from dotenv import load_dotenv
    load_dotenv(root/'.env')
    address = ('127.0.0.1', 8000)
    with socket.socket() as probe:
        occupied = probe.connect_ex(address) == 0
```

`__file__`-ը գործարկվող ֆայլի ուղին է։ `parent`-ը վերցնում է դրա պանակը, `chdir`-ը դարձնում է այն աշխատանքային պանակ, ապա `load_dotenv`-ը կարդում է կարգավորումները։ `connect_ex`-ի զրո պատասխանը նշանակում է, որ հասցեում արդեն մեկը լսում է։ Եթե համարը զբաղված է, `start.py:19–34`-ում ծրագիրը կարդում է `/openapi.json`-ը՝ գործառույթների մեքենայաընթեռնելի նկարագրությունը։ `HaySub` վերնագիրը և `DELETE /api/subtitle-files/{identity}` գործողության առկայությունն են որոշում՝ կարո՞ղ ես բացել առկա ծառայությունը։ Այդ դեպքում երևում է `HaySub is already running: http://127.0.0.1:8000`։ Եթե գտել է հին տարբերակ կամ ուրիշ ծառայություն, հաղորդագրությունը տարբեր է։ Այս ստուգման հասցեն միշտ 8000 է, անգամ եթե `PORT` կարգավորումը փոխվել է։

`start.py:23–30` · `main`

```python
            if schema.get('info', {}).get('title') == 'HaySub':
                route = schema.get('paths', {}).get('/api/subtitle-files/{identity}', {})
                if 'delete' not in route:
                    print('An older HaySub server is running. Stop it with Ctrl+C in its terminal, then run this command again.')
                    return 1
                print('HaySub is already running: http://127.0.0.1:8000')
                print('To load code or .env changes, stop it with Ctrl+C in its terminal first.')
                return 0
```

**2. Ազատ համարի դեպքում** `start.py`-ն կանչում է մեկ այլ ֆայլի `main`-ը՝ այստեղ նրան տալով `serve` անունը։

`start.py:36–38` · `main`

```python
    from app.serve import main as serve
    serve()
    return 0
```

`app/serve.py:35–37` · `main`

```python
    if os.getenv('HAYSUB_MEDIA_WORKER_ENABLED')=='1' and os.getenv('HAYSUB_MEDIA_STORAGE'):
        threading.Thread(target=supervise,daemon=True).start()
    try:uvicorn.run('app.main:app', host='0.0.0.0' if os.getenv('HAYSUB_PUBLIC')=='1' else '127.0.0.1', port=int(os.getenv('PORT','8000')), workers=1,access_log=False)
```

`Uvicorn`-ը սպասում է մուտքային կապերի և հարցումները հանձնում Python հավելվածին։ `app.main:app` նշանակում է «բացիր `app/main.py`-ը և վերցրու այնտեղի `app` օբյեկտը»։ `workers=1`-ը մեկ վեբ գործընթաց է։ Նախորդ երկու տողերը միայն կարգավորված դեպքում են առանձին գործարկում մեդիա ֆայլեր մշակող `worker`-ը՝ երկարատև գործերն անող ծրագիրը։

**3. Սկզբում կազմվում է հասցեների քարտեզը։** `route`-ը հասցեի և գործողության կապն է, `middleware`-ը՝ հարցման ճանապարհին կատարվող ընդհանուր ստուգում։ `/static`-ով սկսվող հարցումների համար նշվում է էջերի, ձևավորման և վարքագծի ֆայլերի պանակը։

`app/main.py:51–55` · `app`

```python
app = FastAPI(title='HaySub', lifespan=lifespan)
app.middleware('http')(public.access_control)
app.include_router(public.router)
app.include_router(media_api.router)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
```

Հարցումներ ընդունելուց առաջ Uvicorn-ն օգտագործում է `lifespan`-ը՝ հավելվածի գործարկման և կանգնեցման քայլերը։ `SQLite`-ը ֆայլում պահվող տվյալների բազա է․ այստեղ մնում են աշխատանքի ընթացքն ու գրադարանի գրառումները։ `index_completed_translations`-ը ստուգում է նախկին ավարտված գործերը։ `catalog_sync.sync`-ը ըստ կարգավորման թարմացնում է հրապարակման պանակը։ `await`-ը նշանակում է, որ այս քայլի ավարտին պետք է սպասել, իսկ `yield`-ից հետո արդեն կարելի է սպասարկել էջերը։

`app/main.py:38–45` · `lifespan`

```python
async def lifespan(app):
    public.validate_configuration()
    if os.getenv('HAYSUB_DB'):
        storage.DB = Path(os.environ['HAYSUB_DB'])
    index_completed_translations()
    from app import catalog_sync
    await asyncio.to_thread(catalog_sync.sync)
    yield
```

`app/main.py:536–539` · `index_completed_translations`

```python
def index_completed_translations():
    # Recover older completed persisted jobs; never invent files from hash-only caches.
    for saved in storage.unindexed_file_jobs():
        archive_completed_translation(saved)
```

`app/catalog_sync.py:33–36` · `sync`

```python
def sync():
    global _fingerprint, _status
    if not enabled():
        return 'disabled'
```

Եթե կան դեռ չգրանցված, պահպանված գործեր, `archive_completed_translation`-ը ստուգում է դրանց ամբողջականությունը և արխիվացնում պատրաստի տեքստը․ սա կկարդաս [թարգմանության գլխում](#translation)։ Առաջին դասում անջատած `sync`-ը վերադարձնում է `'disabled'`։

**4. Վերջապես դու բացում ես հասցեն։** `HTTP`-ը էջեր ու տվյալներ պահանջելու և վերադարձնելու հաղորդակարգն է։ `GET /` նշանակում է «տուր սկզբնական էջը»։ `@app.get('/')` գրառումը այդ հարցումը կապում է `index`-ին։ Տեղական ռեժիմում պատասխանը ֆայլ է։ Հանրային ռեժիմում կառավարումը փոխանցվում է `app/public.py`-ի `viewer_catalog`-ին։

`app/main.py:58–61` · `index`

```python
@app.get('/')
def index():
    if public.public_mode():return public.viewer_catalog()
    return FileResponse(ROOT / 'static' / 'index.html')
```

`app/public.py:207–209` · `viewer_catalog`

```python
@router.get('/catalog')
def viewer_catalog():
    template=(STATIC/'public.html').read_text(encoding='utf-8')
```

`HTML`-ը էջի կառուցվածքի լեզուն է, իսկ `CSS`-ը նկարագրում է դրա տեսքը։ Տեղական `HTML`-ը սովորեցնում է նաև գտնել, թե որ կոդն է իրոք կանչվում․ փնտրիր տեսած վերնագիրը, ապա ներքևում կարդա `script` տարրերը։

`static/index.html:7–10` · `ֆայլի ընտրության ձևը`

```html
<form id="file-translation-form" class="file-translation-form">
<label for="translate-file">Ենթագրերի ֆայլ<input id="translate-file" type="file" accept=".srt,.vtt" required></label>
<button id="translate-file-submit" type="submit" class="primary">Թարգմանել հայերեն <span>→</span></button>
</form>
```

`static/index.html:43–43` · `էջի միացրած ծրագրերը`

```html
</section></main><script src="/static/file-translator.js"></script><script src="/static/translation-library.js"></script><script src="/static/media-upload.js"></script><script src="/static/poster-editor.js?v=full-image"></script><script src="/static/media-owner.js?v=automatic-badge-2"></script><script src="/static/media-sources.js"></script><script src="/static/watch.js"></script></body></html>
```

Էջի կոճակն արդեն տեսանելի է, իսկ `file-translator.js`-ը դրան արձագանք կտա ֆայլ ուղարկելիս։ Մեկ ուրիշ միացված ֆայլ՝ `media-owner.js`-ը, անմիջապես կանչում է `init`-ը (տող 281)։ Նախ հարցնում է հասանելի կարգավորումները, հետո՝ ֆիլմերն ու ենթագրերի գրադարանը։

`static/media-owner.js:255–260` · `init`

```javascript
  async function init(){
    try{
      settings=await api('/api/owner/media/config');
      if($('hosted-upload-submit'))$('hosted-upload-submit').disabled=!settings.configured;
      if($('hosted-folder-controls'))$('hosted-folder-controls').hidden=!settings.video_folder;
      await Promise.all([refresh(),refreshLibrary()]);
```

`app/media_api.py:89–93` · `config`

```python
@router.get('/api/owner/media/config')
def config():
    try:
        backend=stores.store()
        from app.local_videos import folder
```

`config`-ը փորձում է ստանալ կարգավորված պահոցը։ `app/media_api.py:94–96`-ում վերադարձնում է կա՛մ հատկությունները, կա՛մ `configured=False` և պատճառը։ `refresh`-ի հաջորդ հարցումը հասնում է `owner_list`-ին։ Դատարկ ցուցակի դեպքում էլ էջն աշխատում է։

`static/media-owner.js:225–228` · `refresh`

```javascript
      const items=(await api('/api/owner/media')).filter(item=>!['bin','deleting'].includes(item.state)),ids=new Set(items.map(item=>item.id));
      for(const [id,row] of rows)if(!ids.has(id)){closeRowPreview(row);row.root.remove();rows.delete(id);}
      for(const item of items){if(rows.has(item.id))apply(rows.get(item.id),item);else card(item);}
      $('hosted-empty').hidden=!!items.length;
```

`app/media_api.py:110–111` · `owner_list`

```python
@router.get('/api/owner/media')
def owner_list():return [summary(item) for item in listed_videos()]
```

`refresh`-ը պատասխանի ամեն ֆիլմի համար թարմացնում կամ ստեղծում է քարտ։ Ահա թե ինչու ժամանած `HTML`-ը ցույց է տալիս ձևը, իսկ քո տեսադարանի պարունակությունը կարող է մի փոքր ավելի ուշ երևալ։ `static/app.js`-ում ևս կգտնես նվագարկիչի կոդ, բայց վերևի `script` ցանկը ցույց է տալիս այս էջի իրական մուտքերը։ Ներկայիս YouTube տարբերակը սկսվում է [Chrome հավելումից](#extension)։

**Արժե առանձին ուսումնասիրել — `HTTP request lifecycle`։** Սովորիր հասցեից գտնել այն `function`-ը, որը պատասխան է վերադարձնում։ Վերցրու `GET /`-ը՝ `app/main.py`-ի `index`, հետո կրկնիր `GET /api/owner/media`-ով։

**Փորձիր ինքդ։** Տեղական հավելվածն աշխատելիս երկրորդ PowerShell պատուհանում, նախագծի արմատից, ստուգիր դրա պատրաստ լինելը։

```powershell
(Invoke-RestMethod 'http://127.0.0.1:8000/healthz').status
```

Պետք է տեսնես `ok`։ Այստեղ ստուգվում է նաև բազայի կապը։ Այնուհետև էջում բացիր Chrome-ի `DevTools`-ը՝ մշակողի գործիքները (`F12`), ընտրիր `Network`՝ հարցումների ցանկը, և թարմացրու էջը։ Փնտրիր `/`, `file-translator.js` և `/api/owner/media`։ Հաջող հարցման `200` թիվը նշանակում է, որ պատասխանն ուղարկվել է։

`app/public.py:126–130` · `health`

```python
@router.get('/healthz')
def health():
    with storage.connect() as db:
        db.execute('SELECT 1')
    return {'status':'ok'}
```

<a id="map"></a>

## 3. Նախագծի քարտեզը և կարդալու հերթը

Կոդն ընթերցելիս կողքիդ պահիր այս չորս բառը։ `Frontend`-ը այն մասն է, որ աշխատում է `browser`-ում։ `Backend`-ը ընդունում է հարցումները, աշխատում բազայի և արտաքին ծառայությունների հետ։ `Test`-ը փոքր ծրագիր է, որը տալիս է հայտնի մուտք և ստուգում ակնկալվող արդյունքը։ `Cache`-ը պահված հաշվարկի արդյունք է․ թարգմանությունը թանկ կամ դանդաղ կարող է լինել, իսկ նույն պայմաններով կրկին հաշվելու փոխարեն կարելի է կարդալ պահպանվածը։

Ստորև ուղիները հաշվում ենք նախագծի արմատից։ Նույնանուն `player.js` կամ `catalog` հանդիպելիս նայիր **ամբողջ ուղուն**։

| Որտեղ կարդալ | Ինչի համար է և ով է օգտագործում | Երբ բացել |
|---|---|---|
| [start.py](start.py), [app/serve.py](app/serve.py), [Start HaySub.bat](Start%20HaySub.bat) | Windows-ից մուտք, արդեն աշխատող ծառայության ստուգում, Uvicorn և ընտրովի ֆոնային աշխատանք։ | Առաջին էջին դեռ չես հասել։ |
| [catalog-site/](catalog-site/) | Պատրաստի դիտման կայք։ `catalog.json`-ը ֆիլմերի ցանկն է։ `catalog-model.js`-ը ստուգում է այն, `catalog.js`-ը կազմում է քարտերը, `player.js`-ը սպասարկում է `watch.html`-ը։ `assets/`-ից էջերը կարդում են իրենց ձևավորումն ու ընդհանուր ծրագրերի տեղական պատճենները։ | Ուզում ես ամենակարճ ճանապարհով ֆիլմից հասնել ենթագրին։ |
| [static/index.html](static/index.html), [static/file-translator.js](static/file-translator.js), [static/translation-library.js](static/translation-library.js) | Սեփականատիրոջ առաջին էջը, ֆայլի ուղարկումն ու ընթացքը, պատրաստի ենթագրի պատմությունն ու գործողությունները։ Դրանք դիմում են Python-ի հասցեներին։ | Հարցը սկսվում է «սեղմեցի այս կոճակը» բառերով։ |
| [app/main.py](app/main.py) | Միացնում է հավելվածը և հասցեները։ Ընդունում է ենթագրերը, կազմակերպում է աշխատանքները, վերադարձնում ընթացքը և ներբեռնվող ֆայլերը։ | Ուզում ես տեսնել, թե էջի հարցմանը ով է պատասխանում։ |
| [app/subtitles.py](app/subtitles.py), [app/captions.py](app/captions.py) | Առաջինը ընթերցում և գրում է ենթագրի ձևաչափերը։ Երկրորդն ընտրված YouTube տեսանյութի համար գտնում ու կարդում է հասանելի ենթագրերը՝ `yt-dlp` փաթեթով։ Երկուսն էլ տվյալներ են տալիս `main.py`-ին։ | Ժամը կամ սկզբնական տեքստը կասկածելի է։ |
| [app/translation.py](app/translation.py), [app/rate_limits.py](app/rate_limits.py), [app/storage.py](app/storage.py) | Առաջինը դիմում է Gemini-ին և ստուգում պատասխանը։ Երկրորդը որոշում է՝ այս պահին նոր հարցում կարելի՞ է անել։ Երրորդը SQLite-ում պահում ու գտնում է արդյունքները։ | Թարգմանություն ես սպասում, ուզում ես բացատրել կրկնվող հարցում կամ հասկանալ՝ ինչ կմնա վերագործարկումից հետո։ |
| [static/public-catalog.js](static/public-catalog.js), [static/watch.js](static/watch.js), [static/media-sources.js](static/media-sources.js), [static/playback-progress.js](static/playback-progress.js) | Python-ով մատուցվող ֆիլմի ցանկը, դիտման էջը, ենթագրի փոխակերպումն ու դիտած տեղի պահպանումը։ Էջերը `static/public.html` և `static/watch.html` են։ | Ֆիլմը բացել ես `/catalog`-ից, `/watch/…`-ով կամ սեփականատիրոջ էջում։ |
| [static/media-owner.js](static/media-owner.js), [static/media-upload.js](static/media-upload.js), [static/poster-editor.js](static/poster-editor.js) | Հավաքում են տեսադարանի քարտերը, կառավարում առկա գործողությունները, մասերով ֆայլ փոխանցելու կոդը և ֆիլմի շապիկի պատկերի խմբագրումը։ | Կոճակի առկայությունը նախ համեմատիր `static/index.html`-ի հետ, հետո նայիր՝ ինչ է ուղարկվում։ |
| [app/media_api.py](app/media_api.py), [app/media_db.py](app/media_db.py), [app/media_store.py](app/media_store.py) | Ֆիլմի հասցեներ, վիճակների գրառումներ և ֆայլերի պահոց։ `S3`-ն առանձին ֆայլեր ցանցով պահելու և կարդալու ծառայությունների հաղորդակցման եղանակ է։ Ծրագիրը կարող է նաև օգտագործել տեղական սկավառակը։ | Տեսանյութը կա, բայց դիտման կամ հրապարակման անցումը հստակ չէ։ |
| [app/media_worker.py](app/media_worker.py), [app/media_formats.py](app/media_formats.py), [app/probe_runner.py](app/probe_runner.py) | Ֆոնային ծրագիրը գտնում է հաջորդ գործը։ Ձևաչափի ստուգումը օգտագործում է `ffprobe` գործիքը՝ ֆիլմի պատկերի ու ձայնի հատկությունները կարդալու համար։ | Ներմուծած տեսանյութը դեռ մշակվում է կամ մերժվել է։ |
| [app/local_videos.py](app/local_videos.py), [app/local_library.py](app/local_library.py), [app/media_sources.py](app/media_sources.py) | Տեղական ֆիլմերի հայտնաբերում, ֆիլմի ու ենթագրի տեղաբաշխում, տեղական կամ հեռակա հասցեի ընտրություն։ Կանչողներն են ֆոնային ծրագիրն ու ֆիլմերի սպասարկող հասցեները։ | Պանակում ֆայլ կա, բայց ցանկում չես գտնում կամ սխալ հասցե է բեռնվում։ |
| [app/public.py](app/public.py), [app/catalog_export.py](app/catalog_export.py), [app/catalog_sync.py](app/catalog_sync.py) | Սեփականատիրոջ մուտք և հրապարակված նյութի տրամադրում։ Արտահանող կոդը պատրաստում է դիտողի կայքի ցանկը, իսկ `sync`-ը որոշում է երբ այն թարմացնել։ | Ուզում ես տարբերել քո բազայի գրառումը և այցելուների տեսած ֆիլմը։ |
| [extension/](extension/) | `manifest.json`-ը Chrome-ին ասում է՝ հավելման որ ֆայլը երբ գործարկել։ `popup.js`-ը պատուհանն է, `background.js`-ը կապվում է Python-ի հետ, `core.js`-ը կարդում է ենթագիրը, իսկ `content.js`-ն աշխատում է տեսանյութի էջի մեջ։ | Տողը պետք է երևա ուրիշի կայքի տեսանյութի վրա։ |
| [tests/](tests/), [extension/tests/](extension/tests/) | `pytest`-ը Python-ի ստուգումները գործարկող ծրագիրն է։ `Node.js`-ը JavaScript է կատարում նաև `browser`-ից դուրս, օրինակ՝ `*.test.cjs` ստուգումները։ `tests/sample.srt` և `extension/sample.srt` փոքր ընթեռնելի օրինակներ են։ | Անորոշ է՝ կոդն ինչպես պետք է պահի իրեն կոնկրետ սահմանային պահին։ |
| [.env.example](.env.example), [requirements.txt](requirements.txt), [requirements.lock.txt](requirements.lock.txt), [Dockerfile](Dockerfile), [render.yaml](render.yaml) | Կարգավորումների օրինակ, փաթեթների թույլատրելի և ճշգրիտ տարբերակներ, սպասարկող միջավայրի կառուցման և Render-ում գործարկելու նկարագրություն։ | Տեղական արդյունքը հասկացել ես և ուզում ես վերարտադրել ուրիշ համակարգչում։ |
| [scripts/](scripts/), [docs/](docs/), [README.md](README.md), [CACHE_RECOVERY.md](CACHE_RECOVERY.md) | Սպասարկման ու փաթեթավորման գործիքներ, նախագծի գործելակերպի ու նախկին փոփոխությունների բացատրություններ։ Արմատի `list_models.py`-ն ու `check_captions.py`-ն ստուգում են ծառայությունները առանձին։ | Ուզում ես կառուցել հրապարակման փաթեթ կամ գտնել որոշման սկզբնական բացատրությունը։ |
| `data/`, `.tools/`, `dist/` | Այս համակարգչի տվյալներ, օժանդակ գործիքներ և կառուցված փաթեթներ։ Նախագծի [.gitignore](.gitignore)-ը նկարագրում է տեղական ֆայլերի բացթողումները։ | Փնտրում ես քո իսկ տեսադարանը, պատրաստի ենթագիրը կամ կառուցված արխիվը։ Թարմ պատճենում դրանց պարունակությունը կարող է այլ լինել։ |

**Առաջարկվող ընթերցման հերթը։** Առաջին նստաշրջան՝ `catalog.json → catalog.js → catalog-site/player.js`։ Հաջորդը՝ `tests/sample.srt → app/subtitles.py → app/main.py → app/translation.py → app/storage.py`։ Այնուհետև ընտրիր մեկ օգտագործող՝ դիտող, սեփականատեր կամ հավելման օգտատեր, և հետևիր աղյուսակի համապատասխան տողին։ Ամեն նոր կանչի մոտ գրի առ երեք բան՝ «ո՞վ կանչեց», «ի՞նչ փոխանցեց», «ո՞վ է օգտագործելու արդյունքը»։

### Ի՞նչ է ցույց տալիս նախագծի պատմությունը

`Git`-ը ծրագրի փոփոխությունները պահող գործիք է։ `Commit`-ը պահված վիճակն ու նախորդ վիճակից տարբերությունն է։ Կարճ համարն այստեղ հղում է կոնկրետ փոփոխությանը։ Ընթացիկ պատմության հաղորդագրությունների մեծ մասը պարզապես `up` է։ Հետևյալ փաստերը երևում են ֆայլերի փոփոխություններից։ Դասերի հերթը **առաջարկվող ուսումնական հերթ է**։ Սկզբնական `6292363`-ում արդեն կան թարգմանությունը, բազան, հավելումը և ֆիլմերի սպասարկումը․ դրանց ստեղծման ներքին հերթը Git-ից որոշել հնարավոր չէ։

| Commit | Ինչ է հաստատում ֆայլերի տարբերությունը | Որ դասին է վերաբերում |
|---|---|---|
| `6292363` | Սկզբնական մեծ գրանցման մեջ արդեն կան `app/translation.py`, `app/media_worker.py`, `extension/content.js` և դրանց ստուգումները։ | Դասընթացի մի քանի անկախ գաղափար նախապես միասին կան։ |
| `b4ad7a3` → `52231df` | Առաջինի մեջ ավելանում են `catalog-site/`-ն ու կառուցման գործիքը, հաջորդում՝ `app/catalog_export.py` և `app/catalog_sync.py`։ | Պատրաստի ցանկի ընթերցում, ապա՝ տեղական տվյալներից դրա պատրաստում։ |
| `06f33f5` → `8dd61e9` | Ֆիլմերի «նոր» նշանը հայտնվում է երկու ցանկերում, ապա դիտողի կողմում ավելանում է ֆիլմի բացվելը հիշելու կոդը։ | Ֆիլմի հատկությունն ու տվյալ դիտողի անձնական վիճակը երկու տարբեր տվյալ են։ |
| `ba03ea9` → `c703706` → `e113264` | Առաջինում ավելացած անձնական սպասարկիչի այցելությունների հաշվառումը երկրորդում հեռացվել է։ Երրորդում արդեն պատրաստի կայքի երկու էջերն են ստանում Google-ի այցելությունների հաշվառման կոդը։ | Պատմության մեջ ֆայլ գտնելիս ստուգիր նաև՝ այսօր ո՞ր էջն է այն օգտագործում։ |
| `fdd3df7` → `31cc353` | Առաջինը փոխում է թարգմանվող խմբերի չափն ու կրկնափորձերը, երկրորդը բյուջեն կապում է գրանցված Google նախագծին։ | Երկու տարբեր պատճառ, թե ինչու նոր թարգմանությունը կարող է ավելի քիչ հարցում անել կամ սպասել։ |

**Արժե առանձին ուսումնասիրել — `git show`։** Այս հրամանը բացում է պահված փոփոխությունը։ Կոդի նպատակի մասին գրված մեկնաբանությունը և քո սեփական ենթադրությունը հեշտ է տարբերել, եթե նայում ես հենց փոփոխված տողերին։

**Փորձիր ինքդ։** Արմատից կատարիր հետևյալ երկու հրամանները։ Առաջինը ցույց է տալիս՝ որ տարբերակում ես։ Երկրորդը բերում է թարգմանչի փոփոխության ամփոփումը։

```powershell
git rev-parse --short HEAD
git show --stat fdd3df7
```

Այս ուղեցույցին համապատասխան պատասխանը `31cc353` է։ Երկրորդ հրամանի ցանկում պետք է տեսնես և՛ `app/translation.py`-ն, և՛ `tests/test_efficient_translation.py`-ն։

<a id="playback"></a>

## 4. Ֆիլմի քարտից մինչև էկրանին երևացող առաջին տողը

Ընտրենք «22 Փամփուշտ» ֆիլմը։ Ինչպե՞ս է նվագարկիչն իմանում, որ 35.120 վայրկյանին էկրանին պիտի գրվի «EuropaCorp կինոընկերությունը ներկայացնում է»։ Սկսենք պատրաստ ֆիլմից։ Ենթագիր թարգմանելն ու հրապարակելը կատարվում են նախապես։ Դիտողի սեղմած Play կոճակից հետո ամեն վայրկյան թարգմանիչ կանչելու կարիք չկա։

### Քայլ 1․ բացել արդեն պատրաստ ցանկը

Այս օրինակում `static site`-ը կայք է, որի էջերն ու տվյալների ցանկը `server`-ը մատուցում է որպես պատրաստ ֆայլեր։ `manifest`-ը ֆիլմերի նկարագրությունը համախմբող ֆայլն է։ Պատրաստման ժամանակ ֆիլմն ու հայերեն ենթագիրը պետք է հասանելի դառնան իրենց `URL`-ներով՝ ցանցային հասցեներով։ Այս հավաքածուում դրանք ցույց են տալիս դեպի `Cloudflare R2`՝ ֆայլեր պահող և հասցեով տրամադրող արտաքին ծառայություն։ Ահա ֆիլմի համար պահպանված երկու առանձին հասցեները։

`catalog-site/catalog.json:52-58` · `films` ցանկի մեկ գրառում

```json
      "id": "0e2e2128cc254b83a3fc8f6ab18ab791",
      "title": "22 Փամփուշտ",
      "published": true,
      "video_url": "https://pub-dbe28d8bc48f4d36bd6ae474f7784080.r2.dev/data/videos/22%20%D5%93%D5%A1%D5%B4%D6%83%D5%B8%D6%82%D5%B7%D5%BF.mp4",
      "subtitle_url": "https://pub-dbe28d8bc48f4d36bd6ae474f7784080.r2.dev/data/subtitles/22%20%D5%93%D5%A1%D5%B4%D6%83%D5%B8%D6%82%D5%B7%D5%BF/armenian.srt",
      "subtitle_offset": 0,
      "subtitle_height": 0,
```

`id`-ն ֆիլմի կայուն նույնացուցիչն է։ Երկու ֆիլմ կարող են նույն անունն ունենալ, իսկ դիտման էջին և դիտումը շարունակելու համար հստակ մեկ ֆիլմ է պետք։ `subtitle_offset`-ը ենթագրի ժամերը տեղափոխելու վայրկյանների քանակն է։ `subtitle_height`-ը վերաբերում է տողի ուղղահայաց դիրքին։ Ժամը և բարձրությունը տարբեր չափումներ են։

Փորձի համար բացիր երկրորդ PowerShell պատուհան՝ նախագծի արմատում։ Այս հրամանով Python-ը `catalog-site` պանակի ֆայլերը տալիս է քո համակարգչի 8080 համարով մուտքի կետում։

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory catalog-site --bind 127.0.0.1
```

Հաջողության դեպքում կտեսնես `Serving HTTP on 127.0.0.1 port 8080`։ Բացիր `http://127.0.0.1:8080/` և որոնման դաշտում գրիր `22`։ Պետք է մնա «22 Փամփուշտ» քարտը։ Այս հրամանը սպասարկում է նաև դատարկ տեղային տեսադարանի դեպքում, քանի որ ցանկը գալիս է նախագծում առկա `catalog.json`-ից։ Ֆիլմն առցանց դիտելու համար R2-ի հղումները պետք է աշխատեն և թույլ տան այս կայքի հասցեից բեռնումը։ Աշխատանքն ավարտելիս տվյալ պատուհանում սեղմիր Ctrl+C։ Նույն քայլերը նկարագրված են `docs/STATIC_CATALOG.md:135-143`-ում։

`catalog-site/catalog.js:29-31` · էջը բացվելիս կատարվող գործողություն

```javascript
  (async()=>{try{
    const response=await fetch('catalog.json',{cache:'no-store'});if(!response.ok)throw Error();
    films=model.validate(await response.json());render();
```

`fetch`-ը դիտարկիչի գործառույթ է․ հասցեից պահանջում է տվյալներ։ `await`-ով այս հատվածը սպասում է պատասխանին։ `response.json()`-ը ստացված տեքստը դարձնում է JavaScript-ին հասկանալի արժեք։ `cache:'no-store'`-ն այս հարցման համար խնդրում է նորից բեռնել ցանկը։ Հաջորդ կանչը `catalog-model.js`-ի `validate`-ն է։

`catalog-site/catalog-model.js:22-24` · `validate`

```javascript
      const offset=item.subtitle_offset??0;if(!Number.isFinite(offset)||Math.abs(offset)>86400)throw Error('Invalid subtitle offset.');
      return {...item,title:item.title.trim(),video_url:publicUrl(item.video_url),subtitle_url:publicUrl(item.subtitle_url,true),poster_url:poster,subtitle_offset:offset};
    }).filter(item=>item.published!==false);
```

`validate`-ը ստուգում է ժամանակային շեղման սահմանները, հասցեներն անցկացնում է նույն ֆայլի `publicUrl` ստուգումով (տողեր 3–8), ապա ցանկում է թողնում այն գրառումները, որոնց `published`-ը `false` չէ։ `catalog.js`-ն արդյունքը պահում է `films`-ում և կանչում `render`-ը։

`catalog-site/catalog.js:20-22` · `render`

```javascript
  function render(){
    const query=$('search').value.trim().toLocaleLowerCase(),shown=films.filter(item=>item.title.toLocaleLowerCase().includes(query));
    $('public-videos').replaceChildren(...shown.map(card));
```

`catalog-site/catalog.js:7-8` · `card`

```javascript
  function card(item){
    const link=element('a',undefined,'movie-card');link.href='watch.html?id='+encodeURIComponent(item.id);link.title=item.title;
```

`render`-ը համեմատության համար փոքրատառ է դարձնում երկու տեքստերը և յուրաքանչյուր մնացած ֆիլմի համար կանչում `card`-ը։ `card`-ը վերադարձնում է սեղմվող հղում (`link`, տող 18)։ Մեր քարտի վերջնական հասցեն `watch.html?id=0e2e2128cc254b83a3fc8f6ab18ab791` է։ `id=`-ից հետո գրված արժեքն է հասնում հաջորդ էջին։

### Քայլ 2․ դիտման էջը միացնում է ֆիլմն ու ենթագիրը

`catalog-site/watch.html:14` · `hosted-player` և `armenian-track`

```html
<video id="hosted-player" controls playsinline crossorigin="anonymous" preload="metadata" hidden><track id="armenian-track" kind="subtitles" srclang="hy" label="Հայերեն" default></video>
```

`<video>`-ն դիտարկիչի ներկառուցված նվագարկիչն է։ `controls`-ի շնորհիվ ունի Play կոճակ։ Ներսի `<track>`-ը ժամանակագրված տեքստի ուղի է։ Դրա `srclang="hy"`-ը նշում է հայերենը։ Էջի 17-րդ տողը բեռնում է `assets/media-sources.js`-ը, `catalog-model.js`-ը և `player.js`-ը՝ այդ հերթով։ Բացելիս `player.js`-ը վերցնում է `id`-ն։

`catalog-site/player.js:4` · դիտման էջի սկզբնական ընթերցում

```javascript
  const id=new URLSearchParams(location.search).get('id');
```

`catalog-site/player.js:53-57` · դիտման էջի սկզբնական հարցում

```javascript
    const response=await fetch('catalog.json',{cache:'no-store'});if(!response.ok)throw Error();
    item=globalThis.HaySubCatalog.validate(await response.json()).find(film=>film.id===id);
    if(!item){$('watch-title').textContent='Ֆիլմը հասանելի չէ';message('Վերադարձիր ֆիլմերի ցանկ։');return;}
    progress.markOpened?.(id);
    await load();
```

Էջը կարդում է ցանկը նաև ուղիղ հասցեով բացվելու դեպքում։ `find`-ը ընտրում է հենց այդ ֆիլմը։ Չգտնելու դեպքում տեսնում ես «Ֆիլմը հասանելի չէ»։ Գտնելու դեպքում նշվում է, որ այն արդեն բացել ես, և `load`-ը ստանում է իր տվյալները նույն շրջանակի `item` փոփոխականից։

`catalog-site/player.js:19-26` · `load`

```javascript
    // Keep the media playable even when a separate subtitle request fails.
    let captions=item.subtitle_url,newBlob=null;
    if(captions&&(!/\.vtt(?:$|[?#])/i.test(captions)||item.subtitle_offset)){
      try{
        const response=await fetch(captions,{referrerPolicy:'no-referrer'});if(!response.ok)throw Error();
        const text=globalThis.HaySubMediaSources.srtToVtt(await response.text(),item.subtitle_offset||0);
        if(token!==attempt)return;
        newBlob=URL.createObjectURL(new Blob([text],{type:'text/vtt'}));captions=newBlob;
```

Մեր հասցեն ավարտվում է `.srt`-ով։ `SRT`-ն տեքստային ֆայլի ձևաչափ է, որում ամեն ենթագիր ունի համար, ժամանակային միջակայք և արտասանված տեքստ։ `cue` կանվանենք այսպիսի մեկ ժամանակագրված տողը կամ տողերի խումբը։ `load`-ը հարցում է ուղարկում արտաքին պահոցին։ Պատասխանը ստանալով՝ հայերեն տեքստն ու շեղումը փոխանցում է `srtToVtt`-ին։ `WebVTT`-ն դիտարկիչի `track`-ին հասկանալի ժամանակագրված ձևաչափն է։ Եթե սկզբից իսկ հղումը `.vtt` է և շեղումը զրո է, 21-րդ տողի պայմանը թույլ է տալիս այն միանգամից տալ նվագարկչին։

Այս համակարգչի տեղային տեսադարանում նույն ֆիլմին պատկանող ֆայլն այսպես է սկսվում։ Սա այս աշխատանքային պատճենում ստուգված նյութ է։ Git-ը չի պահպանում այն, իսկ արտաքին պահոցի բովանդակությունը կարող է առանձին փոխվել։ Մաքուր պատճենում նույն հաշվարկը կրկնելու համար ստորև կա նաև նախագծում ընդգրկված փոքր փորձ։

`data/subtitles/22 Փամփուշտ/armenian.srt:1-3` · տեղային նյութի առաջին `cue`

```text
1
00:00:35,120 --> 00:00:38,120
EuropaCorp կինոընկերությունը ներկայացնում է
```

`catalog-site/assets/media-sources.js:4-6` · `srtToVtt`

```javascript
  function srtToVtt(raw,offset=0){
    const text=raw.replace(/^\uFEFF/,'').replace(/\r\n?/g,'\n').trim();
    const seconds=value=>value.replace(',','.').split(':').reduce((total,part)=>total*60+Number(part),0);
```

`raw`-ն ֆայլի տեքստն է։ Տողերի ավարտները նախ միատեսակ են դառնում։ `seconds`-ը `00:00:35,120`-ում ստորակետը փոխում է կետի և ժամերը, րոպեներն ու վայրկյանները վերածում մեկ թվի՝ `35.12`։ Հետո `srtToVtt`-ը բաց տողերով բաժանում է հատվածները։

`catalog-site/assets/media-sources.js:26-36` · `srtToVtt`-ի `SRT` ճյուղ

```javascript
    const blocks=['WEBVTT'];
    for(const block of text.split(/\n\s*\n/)){
      const lines=block.split('\n'),index=lines.findIndex(line=>line.includes('-->'));
      const timing=index<0?null:lines[index].match(/^(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(\d{2,}:\d{2}:\d{2}[,.]\d{3})(?:\s.*)?$/);
      if(!timing)throw Error('Invalid cloud subtitle timestamps.');
      const start=Math.max(0,seconds(timing[1])+offset),end=seconds(timing[2])+offset;
      if(end<=start)continue;
      blocks.push(String(blocks.length)+'\n'+stamp(start)+' --> '+stamp(end)+'\n'+escape(lines.slice(index+1).join('\n')));
    }
    if(blocks.length===1)throw Error('No displayable cloud subtitles.');
    return blocks.join('\n\n')+'\n';
```

Առաջին արդյունքը `WEBVTT` վերնագիրն է։ Կոդը յուրաքանչյուր հատվածում որոնում է `-->`-ը, առանձնացնում երկու ժամերը, յուրաքանչյուրին ավելացնում նույն `offset`-ը և հերթական համարով գրում տեքստը։ `stamp`-ը (տողեր 7–12) կազմում է պահանջվող ժամագրությունը։ `escape`-ը (տող 13) բառացի տեքստում եղած `<`, `>` և `&` նշանները պահպանում է որպես ընթերցելի նիշեր։ Եթե շեղումը սկիզբը տանում է զրոյից առաջ, սկիզբը դառնում է զրո։ Եթե դրանից հետո ավարտը սկզբից ուշ չէ, `continue`-ը բաց է թողնում ամբողջ հատվածը։

Մեր տողի համար արդյունքը `00:00:35.120 --> 00:00:38.120` է։ Այստեղ `offset = 0`։ Նույն տողի համար `offset = 2` տալու դեպքում ժամանակը կլիներ `37.120`-ից մինչև `40.120`։ Թվերը վերաբերում են **ֆիլմի** ժամացույցին․ ֆիլմը դադարեցնելիս այդ ժամացույցն էլ է կանգնում։

Հիմա վերադառնանք `player.js`-ի 24–26-րդ տողերին։ Փոխարկված տեքստից `Blob` է ստեղծվում՝ հիշողության մեջ գտնվող ֆայլի նման տվյալ։ `URL.createObjectURL`-ը դրա համար ժամանակավոր հասցե է տալիս հենց այս դիտարկիչում։ Նախորդ փորձի ուշացած պատասխանը `token!==attempt` ստուգման դեպքում անտեսվում է։

`catalog-site/player.js:30-32` · `load`

```javascript
    if(captions)track.src=captions;else track.removeAttribute('src');
    const old=blob;blob=newBlob;if(old)URL.revokeObjectURL(old);
    track.default=captionsEnabled;
```

`catalog-site/player.js:39-41` · `load` և `track`-ի բեռնում

```javascript
    video.src=item.video_url;video.hidden=false;video.load();
  }
  track.addEventListener('load',subtitles);
```

`track.src`-ը ստանում է նոր ժամանակավոր հասցեն, հինը ազատվում է։ `video.src`-ը ստանում է ֆիլմի իրական հասցեն։ `video.load()`-ը սկսում է բեռնումը։ `track`-ի բեռնման իրադարձությունը կանչում է `subtitles`-ը։

`catalog-site/player.js:7-12` · `subtitles`

```javascript
  function subtitles(){
    if(track.track){
      track.track.mode=captionsEnabled?'showing':'disabled';
      const height=item?.subtitle_height??10;
      for(const cue of track.track.cues||[]){cue.snapToLines=height===0;cue.line=height===0?-1:100-height;cue.lineAlign='end';}
    }
```

`mode='showing'`-ը ուղին տեսանելի է դարձնում։ Այս ֆիլմի `height=0` դեպքում `cue.line=-1` է՝ ներքևի տողի դիրքը։ Սեղմիր Play։ Այժմ հենց դիտարկիչն է համադրում ֆիլմի ընթացիկ ժամանակը `track`-ի միջակայքերի հետ։ Մեր տեղային օրինակի նյութով `35.119` վայրկյանին առաջին տողը դեռ չի երևում։ `35.120`-ից մինչև `38.120`-ից անմիջապես առաջ՝ երևում է, իսկ `38.120`-ին սկսվում է երկրորդ տողը։ Այս ընթացքում ֆիլմը գալիս է իր հասցեից, տողը՝ արդեն բեռնված `track`-ից։ Հայերենը պատրաստի նյութ է, և Play սեղմելը Gemini-ին հարցում չի առաջացնում։

**Ինչու է ընտրված այս ճանապարհը։** `docs/STATIC_CATALOG.md:25-31`-ը բացատրում է շարժական սարքերում ներկառուցված ենթագրերի ընտրացանկն օգտագործելու պատճառը և որ `SRT`-ն փոխարկվում է հիշողության մեջ։ Մեկ այլ լուծում կլիներ տեքստը JavaScript-ով առանձին նկարել տեսանյութի վրա։ Դա ավելի ազատ տեսք կտար, բայց ծրագրին կավելացներ ընթացիկ `cue` գտնելու, տողն անջատելու և ամբողջ էկրանով ցուցադրելու գործը։ Սա երկու մոտեցումների հետևանքների համեմատություն է։ Առանձին `static site`-ի կոդը Git-ի պատմության մեջ ավելացել է `b4ad7a3` փոփոխությամբ։

### Քայլ 3․ վերադարձնել դիտման դիրքը

`localStorage`-ը տվյալ կայքի համար դիտարկիչում պահպանվող փոքր գրառումների պահոց է։ Այստեղ `id`-ն թույլ է տալիս տարբեր ֆիլմերի դիրքերն առանձին պահել։ Նվագարկիչը իր ժամանակը կարդում է, երբ դիրքը փոխվել է կամ դիտումը դադարել է։

`catalog-site/player.js:14` · `save`

```javascript
  function save(){if(ready&&!video.seeking)progress.save(id,video.currentTime,video.duration);}
```

`catalog-site/player.js:45-47` · նվագարկչի իրադարձություններ

```javascript
  video.addEventListener('timeupdate',()=>{if(Date.now()-lastSave>=5000){save();lastSave=Date.now();}});
  video.addEventListener('pause',save);video.addEventListener('seeked',save);
  video.addEventListener('ended',()=>{progress.clear(id);});
```

`timeupdate`-ի ամեն ազդանշանի պահին նախ ստուգվում է՝ անցե՞լ է հինգ վայրկյան։ Դադարի և նոր դիրքի անցնելու ավարտի պահին նույնպես կանչվում է `save`։ Վերջում մաքրվում է գրառումը։ Իրական գրանցումը կատարվում է մյուս ֆայլում։

`catalog-site/assets/playback-progress.js:25-30` · `save`

```javascript
  function save(id,position,duration){
    if(!Number.isFinite(position)||position<0||!Number.isFinite(duration)||duration<=0)return;
    position=Math.min(position,duration);
    if(duration-position<=30){clear(id);return;}
    if(position===0)return;
    try{localStorage.setItem(prefix+id,JSON.stringify({position,duration,updated:Date.now()}));}catch{}
```

Օրինակ՝ 900 վայրկյանանոց ֆիլմի 120-րդ վայրկյանին պահպանվում են դիրքը, տևողությունը և գրելու պահը։ 875-րդ վայրկյանին մնում է 25 վայրկյան, այդ պատճառով նախորդ գրառումը մաքրվում է։ Առանձին պահպանվող «բացվել է» նշանը թույլ է տալիս «ՆՈՐ» պիտակը թաքցնել նույնիսկ առաջին վայրկյաններին (`catalog-site/assets/playback-progress.js:6-13`, `catalog-site/catalog.js:16-17`, փոփոխություն `8dd61e9`)։

`catalog-site/player.js:33-38` · `load`-ի `loadedmetadata` արձագանք

```javascript
    video.addEventListener('loadedmetadata',()=>{
      if(token!==attempt)return;
      const saved=progress.read(id,video.duration),target=position??saved?.position??0;
      if(Number.isFinite(video.duration)&&target>0)video.currentTime=Math.min(target,Math.max(0,video.duration-.1));
      ready=true;lastSave=Date.now();progress.rememberDuration(id,video.duration);subtitles();if(!captionError)message('');
    },{once:true});
```

`metadata`-ն ֆիլմի մասին տեղեկությունն է, օրինակ՝ տևողությունը։ Երբ այն հասանելի է, `progress.read`-ը կարդում է նախորդ պահված գրառումը (`catalog-site/assets/playback-progress.js:15-22`)։ Կրկին բեռնելու ընթացիկ դիրքը նախապատվություն ունի, հետո դիտարկվում է պահպանված դիրքը, հետո՝ զրոն։ `video.currentTime`-ի վերագրումով նվագարկիչը գնում է ընտրված վայրկյանին։ Սովորական բացման ժամանակ հաջորդ Play-ը քո ընտրությունն է։ `docs/PUBLIC_VIEWER.md:11`-ում գրանցված է այս ընտրության սահմանը՝ դիրքը պատկանում է տվյալ կայքին և դիտարկիչին։ Օգտահաշիվ ունենալու դեպքում դիրքը `server`-ում պահելը թույլ կտար դիտումը շարունակել մեկ այլ սարքում, բայց կպահանջեր օգտվողին ճանաչել և պահել նրա պատմությունը։

### Երբ ֆիլմը գալիս է, իսկ ենթագիրը՝ ոչ

`catalog-site/player.js:27` · `load`-ի ձախողված ենթագրի բեռնում

```javascript
      }catch{if(token!==attempt)return;captions='';captionError=true;message('Ենթագրերը չեն բեռնվել։ Ստուգիր ենթագրի հղումը և R2 CORS կարգավորումը։');}
```

Եթե պահոցը չի տալիս ֆայլը, կամ փոխարկման ժամանակ տող 30-ում ստացվել է `Invalid cloud subtitle timestamps.` սխալը, այս `catch`-ը մաքրում է միայն ենթագրի հասցեն։ Էկրանին գրվում է հենց մեջբերման հայերեն նախադասությունը։ Հետո `load`-ի 30-րդ տողը հանում է `track.src`-ը, իսկ 39-րդը շարունակում է բեռնել տեսանյութը։ Անմիջական `.vtt` հղման բեռնման սխալը մշակում է `player.js:42`-ը։ Տեսանյութի և ենթագրի բեռնումներն առանձին պահելու պատճառը գրված է նույն ֆայլի 19-րդ տողի մեկնաբանությունում։

Սկսիր դիտարկիչի `DevTools`-ից՝ այն գործիքներից, որոնցով տեսնում ես էջի հարցումներն ու պատասխանները։ `Network` բաժնում գտիր `.srt` հարցումը։ `404` պատասխանը նշանակում է, որ տվյալ հասցեով նյութը չի գտնվել։ `CORS`-ը այլ կայքի տվյալ կարդալու թույլտվության կանոնն է․ եթե դիտարկիչը հաղորդում է դրա խախտման մասին, ստուգիր՝ արդյոք պահոցը թույլ է տալիս հենց էջի հասցեն, օրինակ՝ `http://127.0.0.1:8080`։ Եթե հարցումը հաջողվել է, բացիր պատասխանի տեքստը, գտիր `-->` տողը և համեմատիր `srtToVtt`-ի 29-րդ տողի ընդունած ձևի հետ։ Նույն հաղորդագրությունը դեռ չի բացահայտում, թե այս պատճառներից որն է տեղի ունեցել։

**Փորձիր ինքդ։** Դիտման էջում բացիր `DevTools → Console`։ Սա JavaScript հրամաններ կատարելու դաշտն է։ Երբ ենթագիրը բեռնվի, այնտեղ կատարիր հետևյալ հրամանը։ Դրա աշխատանքային միջավայրը `watch.html` էջն է։

```javascript
Array.from(document.getElementById('armenian-track').track.cues || [])
  .slice(0, 2).map(cue => [cue.startTime, cue.endTime, cue.text])
```

Եթե արտաքին ֆայլը համընկնում է վերը կարդացած տեղային պատճենին, առաջին եռյակն է `[35.12, 38.12, "EuropaCorp կինոընկերությունը ներկայացնում է"]`։ Ֆիլմը տար մոտ 34-րդ վայրկյան, ընտրիր հայերեն ուղին և սեղմիր Play։ Տեսարանը կարելի է ստուգել նաև առանց արտաքին պահոցի՝ նախագծի վարժության տվյալներով։

`tests/static-catalog.test.cjs:40` · `harness`-ի փորձնական պատասխան

```javascript
    fetch:async url=>{requests.push(url);return url==='catalog.json'?{ok:true,json:async()=>({version:1,films:[entry]})}:{ok:!subtitleFails,text:async()=> '1\n00:00:01,000 --> 00:00:03,000\nՀայերեն'};}});
```

`fixture`-ը նախապես հայտնի փորձնական տվյալ է։ Այստեղ `fetch`-ի փոխարեն ստացվում է `Հայերեն` տեքստը՝ սկզբնական `1–3` վայրկյաններով։ Նույն ֆայլի 4-րդ տողում `subtitle_offset:2` է։ Այսպիսով առաջին ակտիվ պահը `3.000` է, վերջին սահմանը՝ `5.000`։ Կոդում այդ ստուգումը գրված է այսպես։

`tests/static-catalog.test.cjs:45-47` · `static player reads JSON and R2 only…` փորձ

```javascript
  const h=harness();await flush();const video=h.node('hosted-player'),track=h.node('armenian-track');
  assert.deepEqual(h.requests,['catalog.json',film.subtitle_url]);assert.equal(video.src,film.video_url);assert.equal(track.src,'blob:captions');
  assert.match(await h.blobs[0].text(),/00:00:03.000 --> 00:00:05.000/);
```

Նախագծի արմատում՝ PowerShell-ում կատարիր հետևյալ հրամանը։ `Node.js`-ը կարողանում է JavaScript կատարել առանց դիտարկիչ բացելու։ Հրամանը գործարկում է փորձնական ֆիլմով ստուգումները, այդ թվում՝ ձախողված ենթագրի դեպքը (տողեր 61–65)։ Ակնկալիր `fail 0`։ Փորձը ստուգում է ստեղծված տեքստը, հասցեները և նվագարկչի հրահանգները։ Էկրանին տողի իսկապես երևալը ստուգում ես դիտարկիչով։

```powershell
node --test tests/static-catalog.test.cjs
```

**Արժե առանձին ուսումնասիրել։** Որոնիր `HTML video text tracks WebVTT`․ կսովորես՝ ինչ է անում դիտարկիչը Play-ից հետո։ Վերադարձիր `catalog-site/watch.html:14`-ի `<track>`-ին, ապա `catalog-site/player.js:7-12`-ի `mode` և `line` դաշտերին։

<a id="server-player"></a>

## 4բ. Նույն գործողությունը տեղային հավելվածի `/catalog` էջում

Մինչև այստեղ դիտարկիչը պատրաստ ֆայլից գտնում էր ֆիլմի հասցեն։ Եթե ուզում ես աշխատել սեփականատիրոջ պահպանած կամ դեռ նոր հրապարակած ֆիլմերի հետ, բացիր տեղային HaySub-ի `/catalog` էջը։ Այս ճանապարհին `server`-ը կազմում է ֆիլմերի ցանկը և առանձին որոշում՝ կարելի՞ է տվյալ ֆիլմը դիտել։

`app/public.py:207-209` · `viewer_catalog`

```python
@router.get('/catalog')
def viewer_catalog():
    template=(STATIC/'public.html').read_text(encoding='utf-8')
```

Էջի հարցմանը `server`-ը կարդում է `static/public.html`-ը։ Նույն `function`-ի 214–215-րդ տողերը JavaScript-ի և CSS-ի հասցեներին ավելացնում են ֆայլի բովանդակությունից ստացված տարբերակի նշան և վերադարձնում էջը։ Դիտարկիչը `static/public.html:8`-ից բեռնում է `public-catalog.js`-ը։ Դրա 51-րդ տողը կանչում է `load`-ը։

`static/public-catalog.js:45-47` · `load`

```javascript
      const response=await fetch('/api/public/videos',{cache:'no-store'});
      if(!response.ok)throw Error('Չհաջողվեց բեռնել ֆիլմերը։ Փորձիր կրկին։');
      items=(await response.json()).sort((a,b)=>(b.published_at||0)-(a.published_at||0));loaded=true;render();
```

`app/media_api.py:175-179` · `public_videos`

```python
@router.get('/api/public/videos')
def public_videos():
    items=[item for item in listed_videos() if item['published'] and item['state']=='ready']
    items.sort(key=lambda item:item['published_at'] or item['created'],reverse=True)
    return [dict(id=item['id'],title=item['title'],watch_url='/watch/'+item['id'],
```

Առաջին հատվածում հարցումը գնում է `/api/public/videos`։ Երկրորդում `server`-ը վերցնում է ցուցադրելի գրառումները `listed_videos`-ից (նույն ֆայլի 99–107-րդ տողեր) և թողնում պատրաստ ու հրապարակված ֆիլմերը։ Գրառման հետ տալիս է նաև դիտման հասցեն։ `load`-ը, ստանալով պատասխանը, դասավորում է `published_at`-ով՝ նորերը վերևում, և կանչում `render`։ `render`-ը 33-րդ տողում յուրաքանչյուր ֆիլմի համար կանչում է `card`-ը։

`static/public-catalog.js:10-11` · `card`

```javascript
  function card(item){
    const link=element('a',undefined,'movie-card');link.href='/watch/'+encodeURIComponent(item.id);link.setAttribute('aria-label',item.title);link.title=item.title;link.addEventListener('click',remember);
```

`app/media_api.py:503-507` · `watch`

```python
@router.get('/watch/{identity}')
def watch(identity:str):
    if not re.fullmatch('[a-f0-9]{32}',identity):raise HTTPException(404,'Video not found.')
    item=db.get(identity)
    return watch_page(item,owner=False)
```

Քարտի սեղմումը կանչում է `/watch/{identity}` հասցեն։ Python-ի `watch`-ը ստուգում է՝ նույնացուցիչը 32 տասնվեցական նի՞շ է, կարդում է համապատասխան գրառումը և `watch_page`-ին փոխանցում `owner=False`։ Վերջինս կարդում է `static/watch.html`-ը և պատրաստ հրապարակված ֆիլմի համար որոշում հայերեն ուղու ու տեսանյութի աղբյուրները։

`app/media_api.py:515-519` · `watch_page`

```python
    # Unavailable/unpublished pages keep their normal client-side error handling.
    if item and (owner or item['published']) and item['state']=='ready':
        try:access=playback(item,owner=owner)
        except HTTPException:return Response(template,media_type='text/html; charset=utf-8',headers={'Cache-Control':'no-store'})
        for tag_id,local_key,cloud_key in (('hosted-source','video_url','cloud_video_url'),('armenian-track','subtitle_url','cloud_subtitle_url')):
```

`app/media_api.py:441-448` · `playback`-ի արտաքին ֆիլմի ճյուղ

```python
def playback(item,owner=False):
    if item['external_video_url']:
        if item['state']!='ready' or (not owner and not item['published']):raise HTTPException(404,'Video is unavailable.')
        subtitles=item['external_subtitle_url']
        if not subtitles and item['subtitle_key']:
            subtitles=('/api/owner/media/' if owner else '/api/public/hosted/')+item['id']+'/subtitles.vtt'
        return {'id':item['id'],'title':item['title'],'source_type':'cloud','video_url':item['external_video_url'],'subtitle_url':subtitles,
                'cloud_video_url':item['external_video_url'],'cloud_subtitle_url':subtitles,'subtitle_offset':0,'subtitle_height':item['subtitle_height'],'duration':item['duration'],
```

Եթե սեփականատերը նախկինում պահպանել է արտաքին տեսանյութի հասցեն, `playback`-ը վերադարձնում է հենց այդ հասցեն։ Ենթագրի հասցեն կարող է տանել անմիջապես արտաքին ֆայլի կամ, եթե ենթագիրը կցվել է տեսադարանում, HaySub-ի `subtitles.vtt` հասցեին։ `watch_page`-ը 519–526-րդ տողերում պատրաստում և վերադարձնում է ֆիլմի աղբյուրներով HTML-ը։ Դիտարկիչում բեռնված `static/watch.js:6-7`-ը նույնացուցիչից կազմում է դիտման տվյալների հասցեն, իսկ 256-րդ տողում առանձին դիտման էջը կանչում է `connect`-ը։

`static/watch.js:175-180` · `connect`

```javascript
      const response=await fetch(endpoint,{cache:'no-store',referrerPolicy:'no-referrer'});
      if(!response.ok){if(response.status===401)throw Error('Մասնավոր նախադիտման համար մուտք գործիր /admin էջում։');if(response.status===404)throw Error('Տեսանյութը հասանելի չէ կամ հրապարակված չէ։');throw Error('Նվագարկիչն այժմ հասանելի չէ։ Փորձիր կրկին։');}
      const access=await response.json();if(token!==operation)return;
      if(!ownerPlayback)progress?.markOpened?.(endpoint.split('/').at(-2));
      const subtitleUrl=cloudTrack?access.cloud_subtitle_url:access.subtitle_url;
      const captions=await prepareCaptions(subtitleUrl,!!(subtitleUrl&&(access.source_type==='cloud'||cloudTrack&&/\.srt(?:$|[?#])/i.test(subtitleUrl))),access.subtitle_offset||0);
```

`app/media_api.py:496-500` · `public_access`

```python
@router.get('/api/public/hosted/{identity}/playback')
def public_access(identity:str):
    item=item_or_404(identity)
    if not item['published'] or item['state']!='ready':raise HTTPException(404,'This video is unavailable or has not been published.')
    return playback(item)
```

Դիտարկիչի առանձին հարցումը `server`-ին թույլ է տալիս նորից ստուգել ֆիլմի վիճակը։ Վերցրու երբեմնի հրապարակված ֆիլմի հին հղումը․ եթե սեփականատերն այն հանի հրապարակումից, `public_access`-ը կվերադարձնի `404`։ `connect`-ի 176-րդ տողում հենց այդ պատասխանը վերածվում է «Տեսանյութը հասանելի չէ կամ հրապարակված չէ։» հաղորդագրության։ HTML էջն ինքնին կարող է հաջողությամբ բացված լինել․ տվյալը պարզելու համար անհրաժեշտ է նայել հատկապես `/playback` հարցմանը։ Այս տարբերությունն ուղղակիորեն ստուգում է `tests/test_viewer.py:69-75`-ը։

Պատրաստ ֆիլմի դեպքում `public_access`-ը կրկին կանչում է `playback`-ը։ Տեղային կառավարվող ֆիլմի և ժամանակավոր դիտման հասցեով պահոցի ճանապարհները տես `app/media_api.py:450-470`-ում։ Այժմ դիտարկիչին պետք է հայերեն ուղին։ Արտաքին `SRT`-ի դեպքում `connect`-ը կանչում է `prepareCaptions`-ը։

`static/watch.js:104-107` · `prepareCaptions`

```javascript
  async function prepareCaptions(url,convert=false,offset=0){
    if(!url||!convert)return {url,blob:null};
    let response;
    try{response=await fetch(url,{cache:'no-store',referrerPolicy:'no-referrer'});}
```

`static/watch.js:110-112` · `prepareCaptions`

```javascript
    const text=globalThis.HaySubMediaSources.srtToVtt(await response.text(),offset);
    const blob=URL.createObjectURL(new Blob([text],{type:'text/vtt'}));
    return {url:blob,blob};
```

Անմիջական `VTT` հասցեն, որի համար փոխարկում չի պահանջվել, վերադառնում է 105-րդ տողում։ Եթե փոխարկում է պետք, կիրառվում է արդեն ծանոթ `srtToVtt`-ը՝ այս անգամ `static/media-sources.js:4-36`-ից։ Այստեղ կոդը նույնն է, ինչ `catalog-site/assets/media-sources.js`-ում։ `server`-ում պահված `cue`-երով հանրային ուղու դեպքում ժամանակի շեղումը կիրառելու տեղը կարելի է տեսնել առանձին։

`app/media_api.py:488-493` · `public_cloud_subtitles`

```python
@router.get('/api/public/hosted/{identity}/subtitles.vtt')
def public_cloud_subtitles(identity:str):
    item=item_or_404(identity)
    if not item['published'] or item['state']!='ready' or not item['subtitle_key']:
        raise HTTPException(404,'Subtitle track not available.')
    return Response(webvtt(json.loads(item['subtitle_cues']),item['subtitle_offset']),media_type='text/vtt; charset=utf-8',headers={'Cache-Control':'no-store'})
```

`app/media_formats.py:39-45` · `webvtt`

```python
    blocks=['WEBVTT']
    for cue in cues:
        start=max(0,cue['start']+offset);end=cue['end']+offset
        if end<=start:continue
        # Entity escaping is required: WebVTT has its own markup, even without HTML overlays.
        text=html.escape(cue['source'],quote=False)
        blocks.append(f'{len(blocks)}\n{timestamp(start)} --> {timestamp(end)}\n{text}')
```

Երբ դիտարկիչը պահանջում է այդ `subtitles.vtt` հասցեն, `public_cloud_subtitles`-ը ստուգում է գրառումը, բացում պահված `subtitle_cues`-ը և `webvtt`-ին տալիս է `subtitle_offset`-ը։ `webvtt`-ը յուրաքանչյուր շարքի սկիզբն ու վերջը տեղաշարժում է, ստացված տողերը վերադարձնում որպես `UTF-8`՝ հայերենը պահպանող նիշերի կոդավորմամբ (տող 47)։ Շեղումն արդեն պատասխանի ժամերի մեջ է։ Մասնավորապես արտաքին ֆիլմի՝ `server`-ում կցված ուղու դեպքում վերևում կարդացած `playback`-ը դիտարկիչին տալիս է `subtitle_offset:0`, որպեսզի պատրաստի ժամանակները մնան իրենց տեղում։

`static/watch.js:184-187` · `connect`

```javascript
      savedHeight=validHeight(access.subtitle_height??10);height=draftHeight??savedHeight;updateHeightEditor();
      loadMedia(cloudVideo?access.cloud_video_url:access.video_url,captions,position,speed,wasPlaying||playSelection,token);
      playSelection=false;
      timer=setTimeout(()=>connect(true),Math.max(1000,(access.expires_in-30)*1000));
```

`static/watch.js:114-119` · `useCaptions`

```javascript
  function useCaptions(captions){
    captionsAssigned=!!captions.url;
    const previous=subtitleBlob;subtitleBlob=captions.blob;
    if(captions.url)track.src=captions.url;else track.removeAttribute('src');
    if(previous)URL.revokeObjectURL(previous);
    if($('watch-subtitles'))$('watch-subtitles').disabled=!captions.url;
```

`static/watch.js:138-141` · `loadMedia`

```javascript
    useCaptions(captions);source.src=url;mediaAssigned=true;
    if(stage)stage.hidden=false;
    video.hidden=false;if($('watch-controls'))$('watch-controls').hidden=false;video.load();
    if(play)video.play().catch(()=>{if(token===operation)message('Video loaded. Click the player’s Play button to start.');});
```

`connect`-ը ընտրում է տեսանյութի հասցեն, կարդում պահպանված բարձրությունը և հղումներն ուղարկում `loadMedia`-ին։ Այն նախ կանչում է `useCaptions`-ը, որը հասցեն տալիս է `track.src`-ին, այնուհետև նշանակում է `source.src`-ը և սկսում բեռնումը։ Առաջին սովորական բացման ժամանակ `wasPlaying` և `playSelection` արժեքները կեղծ են․ ֆիլմը սպասում է քո Play-ին։ Ժամանակավոր հասանելիության դեպքում 187-րդ տողում նախատեսված է տվյալների նոր հարցում ժամկետի ավարտից մոտ 30 վայրկյան առաջ։ Սրանով հնարավոր է երկար ֆիլմ դիտել՝ ստանալով նոր հասցե, երբ նախորդը մոտենում է ժամկետին։ Ավելացած բարդությունն ընթացիկ դիրքը և նվագարկման վիճակը վերականգնելն է (`static/watch.js:126-136`)։ Այս նպատակը հետևություն է կոդից։

**Եթե կարդում ես YouTube-ի հին կոդը։** Նախագծում կա նաև `static/player.js`՝ ներկառուցված YouTube նվագարկչի համար ժամանակը հաշվարկող ավելի հին կոդ։ Ներկայիս գլխավոր էջի վերջին տողը բեռնում է `static/watch.js`-ը (`static/index.html:43`)։ `static/app.js`-ի `sync`-ը առանձին օրինակ է՝ իր իսկ փորձերով (`tests/playback-ui.test.cjs:14`)։

`static/player.js:4-10` · `activeCues`, `subtitleState`

```javascript
  function activeCues(cues, seconds, offset=0){
    const t=seconds-offset;
    return cues.filter(c=>c.start<=t && t<c.end && !music.isMusicOnly(c.source||c.text)).map(c=>typeof c.source==='string'?{...c,source:music.withoutMusicLines(c.source)}:c);
  }
  function subtitleState(cues, translated, seconds, offset=0){
    const active=activeCues(cues,seconds,offset);
    return {active,waiting:active.some(c=>!translated[String(c.id)])};
```

Այս տարբերակում ժամացույցի ընթացիկ արժեքից հանվում է շեղումը։ Օրինակ՝ `start=1`, `end=3` և `offset=2` դեպքում նվագարկչի `3` վայրկյանին համեմատվում է `3−2=1`, և տողն ակտիվ է։ `5` վայրկյանին ստացվում է `5−2=3`, և ավարտի սահմանն արդեն անցած է։ Ավելի վեր `SRT`-ի ժամերին `+2` էինք գումարում։ Երկու հաշվարկն էլ հասնում են նույն՝ `[3,5)` միջակայքին, որտեղ ձախ սահմանը ներառված է, աջը՝ բաց։ Այս նույնացումը կօգնի ժամանակի սխալ փնտրելիս նախ որոշել՝ որ նվագարկչի կոդն ես կարդում։

**Փորձիր ինքդ։** Գործարկված տեղային HaySub-ում բացիր `/catalog`, հետո `DevTools → Network`։ Թարմացրու էջը։ `/api/public/videos` պատասխանը ցուցակ է. դատարկ ցանկի դեպքում էջը կգրի «Դեռ հրապարակված ֆիլմեր չկան։ Նոր ֆիլմերը կհայտնվեն այստեղ։» (`static/public-catalog.js:31-36`)։ Եթե ցանկն ունի ֆիլմ, սեղմիր դրա քարտը և գտիր առանձին `/playback` հարցման `video_url` և `subtitle_url` դաշտերը։ Դատարկ տեղային տեսադարանի դեպքում պատրաստ ու չհրապարակված ֆիլմի տարբերությունը ստուգիր նախագծի արմատից այս հրամանով։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_viewer.py::test_direct_watch_refresh_unpublished_deleted_and_owner_tools
```

Այս ստուգումը ստեղծում է իր փորձնական ֆիլմը և ստուգում նաև նախկին դիտման հղումը։ Սպասվող արդյունքը `1 passed` է։

**Արժե առանձին ուսումնասիրել։** Որոնիր `HTTP status codes and browser Network panel`։ Դրանք օգնում են տարբերել «էջը բացվեց» և «ֆիլմի տվյալները ստացվեցին» դեպքերը։ Կրկին համեմատիր `app/media_api.py:503-507`-ի էջի հարցումը և `app/media_api.py:496-500`-ի տվյալների հարցումը։

<a id="subtitles"></a>

## 5. Ինչպե՞ս է ֆայլի մի տողը դառնում ժամանակով ենթագիր

Դիտելու համար բավական է պատրաստ հայերեն ֆայլը։ Իսկ եթե ֆիլմի հեղինակը քեզ ուղարկել է բնագիրը, նախ պետք է իմանաս, թե որ տողը որ պահին է հնչում։ Այդ կապը գրված է հենց ֆայլում։ `SRT` և `WebVTT` տեքստային ձևաչափեր են․ երկուսն էլ պահում են ենթագրի սկիզբը, վերջը և տեքստը։ Այդ երեքը միասին կոչվում են `cue`։ Կարդա նախագծում եղած առաջին օրինակը։

`tests/sample.srt:1–3`

```text
1
00:00:01,000 --> 00:00:04,000
Hello, welcome to HaySub.
```

`1`-ը այս ֆայլի առաջին հատվածի համարն է։ Տեքստը պետք է երևա 1 վայրկյանից մինչև 4 վայրկյանի սահմանը։ Ստորակետից հետո երեք թվանշանը միլիվայրկյաններն են։ Երկրորդ հատվածն սկսվում է ուղիղ 4 վայրկյանին։ HaySub-ին պետք է այնպիսի ներկայացում, որ հարցին՝ «հիմա 2.5 վայրկյան է, ո՞րն է տողը», հնարավոր լինի պատասխանել թվեր համեմատելով։

### Քայլ 1․ բացիր ֆայլը և գտիր դրա ընթերցողին

Տեղային կառավարման էջում ընտրիր «Ենթագրերի ֆայլ»։ `static/index.html:7–10`-ի ընտրիչի անունը `translate-file` է։ Ֆայլ ընտրելն արդեն գործարկում է ուղարկումը (`static/file-translator.js:98–100`)։ `FormData`-ն browser-ի միջոցն է՝ մեկ հարցման մեջ անունով դաշտեր ու ֆայլեր ուղարկելու համար։ Այստեղ կարևոր է դաշտի անունը․ Python-ի կողմը հենց `subtitles` է սպասում։

`static/file-translator.js:110–113` · `form`-ի `submit` մշակիչ

```javascript
      const data=new FormData();data.append('subtitles',file);
      const state=await request('/api/subtitle-files',{method:'POST',body:data});
      identity=state.id;remember(identity);render(state);
      if(state.running)timer=setTimeout(poll,1000);
```

Browser-ը կազմում է տվյալները, `POST` հարցումով ուղարկում ֆայլը, պատասխանից հիշում աշխատանքի `id`-ն և ցուցադրում վիճակը։ `job`-ը մեկ վերբեռնման աշխատանքն է․ այն կարող է դեռ ընթանալ, երբ պատասխանն արդեն հասել է։ Քայլերի հերթականությունը կարդալու համար ժամանակավորապես կանգ առ `await request(...)` տողի վրա և անցիր Python-ի համանուն հասցեին։

`app/main.py:388–396` · `create_file_translation`

```python
@app.post('/api/subtitle-files')
async def create_file_translation(subtitles: UploadFile = File(...)):
    try:
        filename = Path((subtitles.filename or '').replace('\\', '/')).name
        if Path(filename).suffix.lower() not in ('.srt', '.vtt'):
            raise ValueError('Upload an .srt or .vtt subtitle file.')
        original_bytes = await subtitles.read(2 * 1024 * 1024 + 1)
        cues = parse_subtitles(original_bytes, allow_empty_cues=True)
        prepared = is_armenian_subtitle_file(cues)
```

Սկզբում վերցնում է միայն ֆայլի անունը, ստուգում վերջավորությունը և կարդում առավելագույնը 2 MiB-ից մեկ byte ավելի։ `byte`-ը տվյալների չափման միավոր է, `MiB`-ը՝ 1 048 576 byte։ Մեկ ավելորդ byte-ը բավական է մեծ ֆայլը մերժելու համար՝ առանց այն ամբողջությամբ կարդալու։ `parse_subtitles`-ը `parser` է՝ ֆայլի տեքստը ծրագրում օգտագործելի տվյալների վերածող մաս։ Այն ստուգում է չափը և `UTF-8`-ով կարդում տեքստը (`app/subtitles.py:66–72`)։ `UTF-8`-ը տառերը byte-երով գրելու կանոն է․ դրա շնորհիվ նույն ֆայլում պահպանվում են նաև հայերեն տառերը։

`app/subtitles.py:81–85` · `parse_subtitles`

```python
        times = lines[index].split('-->')
        start, end = seconds(times[0].strip()), seconds(times[1].strip().split()[0])
        content = '\n'.join(lines[index + 1:]).strip()
        if not preserve_text:
            content = html.unescape(re.sub(r'<[^>]*>', '', content)).strip()
```

`-->` նշանի երկու կողմերից `seconds`-ը ժամանակները դարձնում է թվեր։ Այն ստորակետը փոխարինում է կետով և ժամերը, րոպեներն ու վայրկյանները գումարում՝ համապատասխան կշիռներով (`app/subtitles.py:57–63`)։ Հաջորդ տողերը դառնում են տեքստ։ Սովորական ներմուծման ժամանակ, օրինակ, `<i>Hello</i>`-ից մնում է `Hello`։

`app/subtitles.py:99–103` · `parse_subtitles`

```python
        if cues and start < cues[-1]['start']:
            raise ValueError('Subtitle timestamps must be in order.')
        cues.append(dict(id=len(cues) + 1, start=start, end=end, source=content))
        if len(cues) > 10000:
            raise ValueError('Maximum 10,000 subtitle cues.')
```

Արդյունքն ավելանում է ցուցակին՝ տեղային հերթական համարով։ `tests/sample.srt`-ի առաջին գրառումն այժմ ունի `id=1`, `start=1.0`, `end=4.0`, `source='Hello, welcome to HaySub.'`։ Սկզբի պահերը պետք է հերթականությամբ աճեն կամ համընկնեն։ Դատարկ ծառայողական հատվածը ներմուծման այս ճանապարհով կարելի է բաց թողնել, իսկ տեքստ ունեցող զրոյական տևողությունը սխալ է (`app/subtitles.py:86–100`)։ Կոդի մեկնաբանությունն այստեղ բացատրում է ընտրությունը․ տևողություն կռահելը կփոխեր ասված խոսքի պահը։

### Քայլ 2․ ճանաչիր արդեն պատրաստ հայերենը

Ինչպե՞ս որոշել՝ ուղարկե՞լ ֆայլը թարգմանության։ `is_armenian_subtitle_file`-ը հերթով նայում է խոսք պարունակող հատվածներին։ Երաժշտական նշումները և միայն թվեր կամ կետադրություն ունեցող տողերը որոշման մեջ չի հաշվում։

`app/main.py:378–385` · `is_armenian_subtitle_file`

```python
        letters = [char for char in cue['source'] if char.isalpha()]
        if not letters:
            continue
        armenian = sum('\u0531' <= char <= '\u0556' or '\u0561' <= char <= '\u0587' for char in letters)
        if armenian <= len(letters) / 2:
            return False
        has_armenian = True
    return has_armenian
```

Ամեն ստուգված հատվածի **տառերի կեսից ավելին** պետք է հայերեն լինի, և գոնե մեկը պետք է անցնի ստուգումը։ Արդեն հայերեն «Բարև»-ով ու հաջորդ `123!` տողով ֆայլը պատրաստ է, իսկ առանձին `Goodbye` տողը ֆայլը տանում է թարգմանության ճյուղ։ Իմ մեկնաբանությամբ՝ կարելի էր վստահել `_hy.srt` անվանը։ Տառերը կարդալը վերանվանված բնագրի դեպքում ավելի ճիշտ որոշում է տալիս, բայց հայերեն տողի մեջ երկար օտար անունները կարող են փոխել արդյունքը։ 

`app/main.py:408–414` · `create_file_translation`

```python
        if prepared:
            job['translated'] = {str(cue['id']): '' if is_music_only(cue['source']) else cue['source'] for cue in cues}
        else:
            restore_file_cache(job)
        complete = len(job['translated']) == len(cues)
        if not complete and not config()['configured']:
            raise ValueError('Set GEMINI_API_KEY and GEMINI_MODEL in .env, then restart the server to translate files.')
```

Պատրաստ հայերենի համար ստեղծվում է `id → տեքստ` համապատասխանություն։ Միայն երաժշտություն նշող հատվածի արժեքը դատարկ է։ Մյուս ֆայլերի դեպքում ծրագիրը նախ կարդում է `cache`-ը՝ ավելի վաղ հաշվված արդյունքների պահոցը։ Եթե պակասող աշխատանք կա, նոր թարգմանության համար անհրաժեշտ են `GEMINI_API_KEY` և `GEMINI_MODEL`։ Առաջինը մասնավոր բանալի է ծառայության մուտքի համար, երկրորդը՝ օգտագործվող թարգմանող ծրագրի անունը։ Եթե ամեն ինչ պատրաստ է, `create_file_translation`-ը դնում է `phase='ready'`, պահպանում աշխատանքն ու գրանցում արդյունքը գրադարանում։ Մնացած դեպքում կանչում է `start(job)` (`app/main.py:415–422`)։

### Քայլ 3․ երբ բնագիրը գալիս է YouTube-ից

Տեղային Chrome extension-ը կարող է նույն մշակման համար գտնել YouTube տեսանյութի պատրաստի ենթագրերը։ `extension`-ը browser-ին հնարավորություն ավելացնող ծրագիր է։ Բացելով դրա պատուհանը և միացնելով թարգմանությունը՝ YouTube տեսանյութի համար կարող ես սկսել նաև առանց ֆայլի։ Ստորև `start`-ն արդեն ստուգել է տեղային ծառայության կարգավորումը (`extension/background.js:35–42`)։

`extension/background.js:43–47` · `start`

```javascript
    const body=new FormData();
    if(!generic){body.append('url',`https://www.youtube.com/watch?v=${id}`);
      body.append('native_captions','true');body.append('summary','true');}
    if(message.text!==undefined)body.append('subtitles',new Blob([message.text],{type:'text/plain;charset=utf-8'}),message.name.slice(0,200));
    const created=await api(generic?'/api/subtitle-files':'/api/videos',{method:'POST',body});
```

`native_captions=true`-ն թույլ է տալիս փնտրել նաև այլ լեզուների բնագրեր։ Եթե ընտրել ես ֆայլ, `subtitles` դաշտն այդ ֆայլն է։ YouTube-ի դեպքում browser-ը երկու տարբերակով էլ դիմում է `/api/videos`։ Python-ի `create`-ը հղումից առանձնացնում է տեսանյութի 11 նիշանոց անունը, առկա ֆայլը տալիս է նույն `parse_subtitles`-ին, ապա գրանցում աշխատանքը (`app/main.py:195–208`, `app/subtitles.py:38–54`)։

`app/main.py:208–213` · `create`

```python
        storage.save_video(identity, video, cues)
        if cues and config()['configured']:
            start(job)
        elif not cues:
            start_captions(identity, job)
        return dict(id=identity, video=video, phase=job['phase'], running=job['running']) if summary else dict(id=identity, **job)
```

Պատրաստ բնագիրն ունի առաջնահերթություն։ Ֆայլով ու կարգավորված թարգմանությամբ գործարկվում է `start(job)`։ Առանց ֆայլի՝ `start_captions`, որն առանձին առաջադրանք է ստեղծում `caption_worker`-ի համար (`app/main.py:183–186`)։ Սխալ ֆայլի դեպքում `parse_subtitles`-ի սխալն անմիջապես վերադառնում է որպես `400` և YouTube-ից փոխարինող ենթագիր չի որոնվում (`tests/test_captions.py:148–157`)։

`app/main.py:147–149` · `caption_worker`

```python
        retrieval = asyncio.to_thread(retrieve_captions, job['video'], allow_any_language=True) if job.get('native_captions') else asyncio.to_thread(retrieve_captions, job['video'])
        result = await asyncio.wait_for(retrieval, timeout=90)
        job['cues'] = result['cues']
```

`asyncio.to_thread`-ը սպասումը փոխանցում է մեկ այլ կատարման հոսքի, որ հիմնական ծրագիրը շարունակի պատասխանել վիճակի հարցումներին։ Այս պատճառը գրված է `caption_worker`-ի նկարագրության մեջ՝ տող 145։ `wait_for`-ը տվյալ աշխատանքի սպասումը սահմանափակում է 90 վայրկյանով։ `retrieve_captions`-ը `yt-dlp` գործիքով վերցնում է տեսանյութի մասին տեղեկությունները՝ `download=False` ընտրությամբ (`app/captions.py:107–121`)։

`app/captions.py:37–40` · `english_tracks`

```python
    for field, source in (('subtitles', 'creator'), ('automatic_captions', 'automatic')):
        tracks = info.get(field) or {}
        for language in sorted(tracks, key=lambda lang: (not lang.startswith('en'), lang != 'en', lang)):
            if not re.fullmatch(r'en(?:[-_][A-Za-z0-9]+)*', language) and not (allow_any_language and re.fullmatch(r'[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*', language)):
```

Նախ դիտարկվում են հեղինակի պատրաստած ենթագրերը, ապա ավտոմատ ստացվածները։ Յուրաքանչյուր խմբում անգլերենն առաջ է։ `allow_any_language=False` սովորական արժեքով անցնում են միայն անգլերենի տարբերակները։ Հաջորդ ստուգումը պահում է `vtt` հղումները և բաց է թողնում այն հասցեները, որոնց `tlang` դաշտը նշանակում է YouTube-ի կողմից այլ լեզվի թարգմանություն (`app/captions.py:42–45`)։

`app/captions.py:127–134` · `retrieve_captions`

```python
                    with ydl.urlopen(track['url']) as response:
                        raw = response.read(MAX_CAPTION_BYTES + 1)
                    cues = parse_automatic_vtt(raw) if source == 'automatic' else parse_subtitles(raw, allow_empty_cues=True)
                    if source == 'automatic':
                        cues = normalize_rolling(cues)
                    if not cues:
                        raise ValueError('Empty captions')
                    return dict(cues=cues, source=source, language=language)
```

Ստացված byte-երը կարդացվում են ինչպես վերբեռնված ֆայլը։ Ավտոմատ ենթագրերի համար `parse_automatic_vtt`-ը հատվածները ճանաչում է ժամանակի տողերով․ YouTube-ը կարող է դատարկ տող թողնել նույնիսկ մեկ հատվածի ներսում (`app/captions.py:79–95`)։ Հետո `normalize_rolling`-ը հաջորդ հատվածի սկզբից հանում է նախորդի վերջում արդեն հանդիպած բառերը, երբ հատվածները համընկնում են կամ իրարից առավելագույնը 0.15 վայրկյան են հեռու (`app/captions.py:48–76`)։ Ստուգիր օրինակը։

`tests/test_captions.py:72–74` · `test_automatic_english_and_rolling_normalization`

```python
    assert result['source'] == 'automatic'
    assert [(c['start'], c['end'], c['source']) for c in result['cues']] == [(1,2,'Hello world'), (2,3,'again'), (3,5,'today')]
    assert [c['id'] for c in result['cues']] == [1,2,3]
```

Սկզբնական երեք տողերն են `Hello world`, `Hello world again`, `world again today` (նույն ֆայլի տող 13)։ Ստացվում է երեք տարբեր ցուցադրվող մաս։ Այլընտրանքը ամբողջ տեքստն ամեն անգամ պահելն է, որի դեպքում այս օրինակում `world` բառը կրկին կհասներ ընթերցողին և թարգմանչին։ Հեղինակի ենթագրերը սովորական ճանապարհով են մշակվում։ Ծրագիրը վերցնում է արդեն գրված ենթագրեր․ այստեղ ձայնը տեքստի վերածող քայլ չկա։

`app/main.py:149–156` · `caption_worker`

```python
        job['cues'] = result['cues']
        job['caption_source'] = result['source']
        job['caption_language'] = result['language']
        storage.save_video(identity, job['video'], job['cues'], result['source'])
        if config()['configured']:
            await worker(job)
        else:
            job['phase'] = 'ready'
```

Արդյունքը վերադառնում է Python-ին։ Այն պահպանում է բնագիրն ու աղբյուրը, և կարգավորված ծառայության դեպքում `worker`-ին փոխանցում նույն `job`-ը, որը հաջորդ գլխում կուսումնասիրես։ YouTube-ի հասանելիության սխալի դեպքում `CaptionError`-ը առաջարկում է վերբեռնել `.srt` կամ `.vtt`, իսկ `caption_worker`-ը դրա բացատրությունը և պատճառի անունը դնում է աշխատանքի վիճակի մեջ (`app/captions.py:10–13`, `app/main.py:157–165`)։ Ակտիվ extension-ը օգտվում է այս հասցեից․ նախագծում մնացած `static/app.js`-ի YouTube հին ձևը ներկայիս կառավարման էջի միացված ծրագրերի ցանկում չկա (`static/index.html:43`)։

**Փորձիր ինքդ։** Ծրագրի արմատում PowerShell-ով գործարկիր առաջին հրամանը։ Այն անմիջապես կարդում է նախագծի օրինակը և տպում առաջին գրառումը։ Հետո գործարկիր երկրորդը․ այն փորձնական ֆայլն ուղարկում է տեղային հավելվածին առանց արտաքին ծառայության։

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from app.subtitles import parse_subtitles; print(parse_subtitles(Path('tests/sample.srt').read_bytes())[0])"
.\.venv\Scripts\python.exe -m pytest -q tests/test_file_translation.py::test_armenian_upload_is_ready_immediately_without_translation_configuration
```

Առաջին արդյունքը պետք է պարունակի `'start': 1.0`, `'end': 4.0` ու բնագիրը։ Երկրորդում սպասիր `2 passed`․ նույն ստուգումն անցնում է թե՛ SRT, թե՛ VTT ֆայլով։ Բացիր `tests/test_file_translation.py:245–259` և հետևիր վերբեռնումից մինչև ներբեռնումն ու աշխատանքի վերականգնումը։

**Արժե առանձին ուսումնասիրել։** Որոնիր `parsing and validation`։ Առաջինը տեքստին կառուցվածք է տալիս, երկրորդը ստուգում է, որ այն համապատասխանի պահանջներին։ Նոր ձևաչափ ավելացնելիս սկսիր `app/subtitles.py:66–106`-ից․ այնտեղ պարզ երևում է՝ սխալ տվյալը որ փուլում է մերժվում։

<a id="translation"></a>

## 6. Ինչպե՞ս թարգմանել միայն պակասող տողերը և պահել աշխատանքը

Մի քանի տողի ժամանակներն արդեն ունես։ Այժմ պատկերացրու 48 անգլերեն հատված, որոնցից մի մասը գուցե արդեն թարգմանել ես։ Նպատակն է ուղարկել պակասող խոսքը, ստուգել ստացած հայերենը և այն կապել ճիշտ համարների հետ։ Այս ընթերցման հերթականությունն ուսումնական է։ Վերբեռնումը, պահպանումը և Gemini-ի աշխատանքը միասին կան արդեն `6292363` առաջին commit-ում։ Հետագա երկու փոփոխության իրական հերթականությունը երևում է `fdd3df7` և `31cc353` փոփոխություններում։

### Քայլ 1․ որոշիր, թե ինչն է նույն աշխատանքը

Երբ նույն ֆայլն ուղարկես այլ անվամբ, արժե գտնել նախորդ աշխատանքը։ `fingerprint`-ը տվյալներից հաշվված նույնացնող արժեք է։ `SHA-256`-ը հաշվարկի այն եղանակն է, որով HaySub-ը նույն մուտքից նույն արժեքն է ստանում։ Անունը հաշվարկի մեջ չկա։

`app/main.py:397–403` · `create_file_translation`

```python
        model = 'imported' if prepared else os.getenv('GEMINI_MODEL','')
        prompt_version = 'prepared-armenian' if prepared else translation.PROMPT_VERSION
        fingerprint = hashlib.sha256(json.dumps([model,prompt_version,cues],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        saved = storage.load_file_job(fingerprint=fingerprint)
        identity = saved['file_identity'] if saved else uuid4().hex
        if identity in file_jobs and file_jobs[identity]['running']:
            return file_status(identity,file_jobs[identity])
```

Ֆայլի աշխատանքի համար հաշվարկի մուտքն է `[model,prompt_version,cues]`։ `model`-ը թարգմանող ծրագրի անունն է։ `prompt`-ը այդ ծրագրին տրվող հրահանգն է, իսկ `prompt_version`-ը նշում է հրահանգների տարբերակը։ Պատրաստի հայերենի համար այստեղ հատուկ արժեքներ են ընտրվում։ Եթե այս նույն աշխատանքն արդեն ընթանում է, կրկնակի ուղարկումն այս ճյուղում վերադարձնում է դրա վիճակը։ Հակառակ դեպքում պահված արդյունքը ստուգվում է `restore_file_state`-ում (`app/main.py:305–325`)։

Մի ամբողջ ֆայլը գտնելուց բացի, հնարավոր է վերականգնել առանձին խմբերի արդյունքները։ `batch`-ը մեկ հարցման համար միավորված հատվածների խումբ է։ `context`-ն այն հարևան տողերն են, որոնք օգնում են հասկանալ խոսքի իմաստը։ Նայիր՝ ինչպես է տարբերվում հենց խմբի `cache key`-ը՝ պահված արդյունքը գտնելու արժեքը։

`app/translation.py:75–77` · `cache_key`

```python
def cache_key(cues, context, model, prompt_version=None):
    version = PROMPT_VERSION if prompt_version is None else prompt_version
    return hashlib.sha256(json.dumps([version, model, cues, context], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
```

Այս ցանկում `cues`-ը պարունակում է նաև համարներ ու ժամանակներ։ Եթե առաջին տողի սկիզբը `1.000`-ից դարձնես `1.500` կամ փոխես հարևան նախադասությունը, կփոխվի խմբի բանալին։ Մեկ բառ թարգմանած լինելուց չի հետևում, որ այն նույն կերպ է թարգմանվելու այլ տեսարանում։ Այս խիստ համեմատության պատճառը փաստագրված է `CACHE_RECOVERY.md:9–16`-ում։ Այլընտրանքը միայն նախադասության տեքստով պահելն է․ դա ավելի շատ հին պատասխաններ կգտներ, բայց կանտեսեր թե՛ համատեքստը, թե՛ մշակման տարբերակը։

`app/main.py:333–337` · `restore_file_cache`

```python
    for size in dict.fromkeys((12, CHUNK_SIZE)):
        for first in range(0,len(cues),size):
            chunk=cues[first:first+size]
            context=cues[max(0,first-3):first]+cues[first+len(chunk):first+len(chunk)+3]
            restored,counts=translation.restore_cached(chunk,context,job.get('model') or os.getenv('GEMINI_MODEL',''))
```

Հին աշխատանքների համար ծրագիրը փորձում է 12-ական և ներկայիս 24-ական խմբեր։ Յուրաքանչյուր խմբի շուրջ վերցնում է առավելագույնը երեք նախորդ և երեք հաջորդ տող և կանչում է `translation.restore_cached`։

`app/translation.py:91–96` · `restore_cached`

```python
    target_key = cache_key(cues,context,model)
    for version in [PROMPT_VERSION,*COMPATIBLE_PROMPTS.get(PROMPT_VERSION,[])]:
        base = cache_key(cues,context,model,version)
        for key in (base,base+':partial'):
            candidate = storage.cached(key)
            if not isinstance(candidate,dict) or not set(candidate).issubset(ids):
```

Այն փորձում է ներկայիս հրահանգի և հստակ թույլատրված հին տարբերակների բանալիները, ինչպես նաև մասնակի՝ `:partial`, արդյունքները։ `COMPATIBLE_PROMPTS`-ի այս տարբերակի ցանկն ունի մեկ հին անուն՝ `eastern-armenian-v1` (`app/translation.py:13–16`)։ Յուրաքանչյուր պիտանի արժեքի տեքստը կրկին ստուգվում է, իսկ հին տարբերակից օգտագործված արդյունքի աղբյուրը գրանցվում է (`app/translation.py:103–115`)։

`app/storage.py:31–34` · `cached`

```python
def cached(key):
    with connect() as db:
        row = db.execute('SELECT result FROM translations WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None
```

`SQLite`-ն տվյալներ պահող ծրագիր է, որը կարող է ամբողջ բազան պահել տեղային ֆայլում։ Այստեղ `SELECT`-ը կարդում է `translations` աղյուսակի մեկ արդյունք։ `JSON`-ը տվյալների տեքստային գրության ձև է․ `json.loads`-ը վերադարձնում է կոդում օգտագործելի արժեքը։ `restore_file_cache`-ը գտած տողերը տեղադրում է `job['translated']`-ում և հաշվում վերականգնվածների թիվը (`app/main.py:338–346`)։ Ուստի նոր վերբեռնման պատասխանը կարող է միանգամից ցույց տալ, օրինակ, `18 / 48` պատրաստ տող։

### Քայլ 2․ ընտրիր հաջորդ խումբը

Եթե դեռ աշխատանք կա, `start`-ը դնում է `running=True` և պլանավորում է `worker(job)`-ը։ `worker`-ը հետին պլանում առաջադրանք կատարող մասն է․ browser-ը կարող է ընթացքում հարցնել, թե որքան աշխատանք է ավարտվել։

`app/main.py:189–192` · `start`

```python
def start(job):
    if not job['running']:
        job.update(running=True, phase='translating', error='', error_code=None, cancelled=False)
        track_job_task(job, worker(job))
```

`app/main.py:94–99` · `worker`

```python
        restore_file_cache(job)
        while True:
            chunks = [cues[i:i + CHUNK_SIZE] for i in range(0, len(cues), CHUNK_SIZE)]
            pending = [chunk for chunk in chunks if any(str(cue['id']) not in job['translated'] for cue in chunk)]
            if not pending:
                break
```

Դիտիր պայմանը ներսից դուրս։ Եթե խմբում **գոնե մեկ** համար բացակայում է `translated`-ից, խումբը մնում է `pending` ցանկում։ Եթե բացակա համար այլևս չկա, շրջանն ավարտվում է։

`app/main.py:101–104` · `worker`

```python
            position = job['position']
            chunk = min(pending, key=lambda c: (0 if c[0]['start'] <= position < c[-1]['end'] else 1, abs(c[0]['start'] - position)))
            first = chunk[0]['id'] - 1
            context = cues[max(0, first - 3):first] + cues[first + len(chunk):first + len(chunk) + 3]
```

Դիտման դեպքում `position`-ն ընթացիկ պահն է։ Առաջնահերթ է այդ պահն ընդգրկող խումբը, այնուհետև որոշիչը խմբի սկզբից մինչև այդ պահն ընկած բացարձակ հեռավորությունն է։ Միայն ֆայլ թարգմանելու դեպքում դիրքը սկզբում `0` է (`app/main.py:79–82`)։ Թարգմանիչը կրկին ստանում է հարևան տողերը։ `worker`-ն արդեն ստուգված տողերը փոխանցում է մասնակի պահոցով և մեկ խմբին տալիս ընդհանուր 165 վայրկյան (`app/main.py:33–34,109–116`)։

**Ի՞նչ փոխվեց և ինչո՞ւ։** `fdd3df7` commit-ում խմբի չափը 12-ից դարձավ 24։ Որպես այլընտրանք՝ մեկ հարցմամբ կարելի էր ուղարկել միայն մեկ տող․ սխալը միշտ այդ տողին կվերաբերեր, բայց 48 տողի դեպքում լավ պատասխաններն էլ կպահանջեին 48 հարցում։ Կարդա `tests/test_efficient_translation.py:43–54`․ 48 տողի առաջին անցման համար փորձնական ծառայությունը ստանում է երկու հարցում, նույն պայմաններով երկրորդի համար՝ զրո։ Ավելի մեծ խմբի սխալ կառուցվածքի դեպքում լրացուցիչ աշխատանք է պահանջվում, և նույն commit-ը փոխեց նաև դրա ուղղման եղանակը։

### Քայլ 3․ հետևիր մեկ հարցման և վերադարձող պատասխանի ճանապարհին

`worker`-ի կանչած `translate`-ը Python-ի կողմից դիմում է արտաքին Gemini ծառայությանը։ Նախ վերականգնում է հասանելի թարգմանությունները։ Ամբողջությամբ պատրաստ կամ միայն երաժշտություն նշող խմբի դեպքում կարող է վերադարձնել արդյունքը նույնիսկ մինչև արտաքին ծառայության համար բանալու ստուգումը (`app/translation.py:86–89,138–149`)։ `[Music]`-ը համարվում է ավարտված դատարկ արժեքով։ «I love music» նախադասության բառերը մնում են խոսք․ համեմատությունը կատարվում է երաժշտական նշումների ամբողջական ցանկի հետ (`app/subtitles.py:7–13,22–35`)։

`app/translation.py:157–160` · `translate`

```python
        while len(completed) < len(cues):
            pending = [cue for cue in cues if str(cue['id']) not in completed]
            target = pending[:repair_size]
            target_ids = {cue['id'] for cue in target}
```

`target`-ի մեջ մտնում են միայն արդյունք չունեցող տողերը։ Եթե 24-ից առաջին 18-ն արդեն պատրաստ են, ուղարկվող նպատակների համարներն են 19-ից 24։ Խմբի մյուս տողերը կարող են ուղարկվել որպես ընթերցելու համատեքստ։

`app/translation.py:164–170` · `translate`

```python
            repair_context = sorted(context + [cue for cue in cues if cue['id'] not in target_ids], key=lambda cue: cue.get('start', 0))
            contents = json.dumps(dict(target=target, context=repair_context, expected_cue_ids=[cue['id'] for cue in target]), ensure_ascii=False)
            await acquire(model, contents, PROMPT + correction, json.dumps(target_schema(target)))
            try:
                response = await asyncio.wait_for(client.models.generate_content(
                    model=model, contents=contents,
                    config=types.GenerateContentConfig(system_instruction=PROMPT + correction, response_mime_type='application/json', response_json_schema=target_schema(target))), timeout=45)
```

Սկզբում հավաքվում է ժամանակով դասավորված համատեքստը, ապա `JSON`-ի մեջ գրվում են թարգմանվող հատվածները, համատեքստն ու սպասվող համարները։ `acquire`-ը տեղ է ամրագրում թույլատրելի հարցումների հաշվարկում։ Վերջում `generate_content`-ը դիմում է Gemini-ին։ `schema`-ն պատասխանի կառուցվածքի պայմանագիրն է․ այստեղ պահանջվում են հենց տվյալ քանակով գրառումներ՝ `id`-ով ու `text`-ով (`app/translation.py:54–62`)։ `PROMPT`-ը հանձնարարում է վերադարձնել հայերեն տեքստը՝ ժամերը թողնելով HaySub-ի տնօրինությանը (`app/translation.py:18–26`)։

`app/rate_limits.py:87–94` · `acquire`

```python
async def acquire(model, contents, instruction, schema):
    # UTF-8 bytes conservatively overestimate text tokens without another API call.
    tokens = len((contents + instruction + schema).encode('utf-8')) + 4096
    while True:
        delay = reserve(model, tokens)
        if not delay:
            return
        await asyncio.sleep(delay)
```

`rate limit`-ը որոշակի ժամանակում թույլատրելի աշխատանքի սահմանն է։ `token`-ն այն միավորն է, որով լեզվական ծառայությունը հաշվում է մշակվող տեքստը։ HaySub-ն այստեղ իրական քանակն իմանալու նոր հարցում կատարելու փոխարեն հաշվարկում է պահպանողական գնահատում՝ `UTF-8` byte-երի թիվը գումարած `4096`։ `reserve`-ը գրանցում է փորձը, վերադարձնում սպասելու տևողություն կամ բարձրացնում սխալ։ Րոպեական սահմանին հասնելիս `acquire`-ը սպասում և նորից է ստուգում։

`app/rate_limits.py:65–70` · `reserve`

```python
        key_hash = hashlib.sha256(os.getenv('GEMINI_API_KEY', '').encode()).hexdigest()
        registered = db.execute('SELECT project FROM gemini_key_projects WHERE key_hash=?', (key_hash,)).fetchone()
        project = registered[0] if registered else ''
        db.execute('DELETE FROM gemini_requests WHERE sent <= ?', (now - 86400,))
        daily = db.execute('SELECT COUNT(*) FROM gemini_requests WHERE model=? AND project=?', (model, project)).fetchone()[0]
        if daily >= rpd:
```

Հաշվելիս կարևոր են և՛ `model`-ը, և՛ նշված Google Cloud նախագիծը։ Չգրանցված բանալիները կիսում են `''` խմբի հաշվարկը։ `reserve`-ը հանում է 24 ժամից հին գրառումները։ Օրական տեղ չլինելու դեպքում հաշվում է մոտակա հասանելի պահն ու վերադարձնում բացատրություն, իսկ րոպեական սահմանները կիրառում է 61 վայրկյանի պատուհանի համար (`app/rate_limits.py:70–84`)։ Սրանք հավելվածի սեփական սահմաններն են։ `31cc353` commit-ը նույն նախագծի բանալիների հաշվառումը միավորեց։ Միայն ընթացիկ ծրագրի հիշողության մեջ հաշվելն ավելի պարզ կլիներ, սակայն վերագործարկելուց կամ միաժամանակ երկու աշխատանք սկսելիս այդ հաշվարկը հուսալի չէր լինի։ Հիմնավորումը կարդա `reserve`-ի տողեր 51–55-ում։

Վերադառնանք Gemini-ի պատասխանին։ `validate_result`-ը այն վերածում է սպասվող կառուցվածքի և առանձին ստուգում համարների հերթականությունը։

`app/translation.py:121–129` · `validate_result`

```python
def validate_result(result, cues):
    parsed = Result.model_validate(result)
    if [c.id for c in parsed.cues] != [c['id'] for c in cues]:
        raise CueIDError('Translation returned missing, duplicated or reordered cue IDs.')
    valid, invalid, reasons = {}, [], []
    for line, cue in zip(parsed.cues, cues):
        try:
            validate_text(line.text, cue)
            valid[str(line.id)] = line.text
```

Եթե սպասել ենք `[19, 20]`, իսկ ստացել `[20, 19]`, համեմատությունը ձախողվում է, մինչև այս պատասխանն օգտագործվի որպես թարգմանություն։ `validate_text`-ը պահանջում է ոչ դատարկ տեքստ՝ գոնե մեկ հայերեն տառով, կամ, եթե բնագրում տառ չկա, դրա ճշգրիտ կրկնությունը (`app/translation.py:65–72`)։ Դա պարզ ստուգում է․ այն չի կարող գնահատել իմաստի ճշգրտությունը։ Հաջող արդյունքը կապվում է համարին՝ օրինակ `{'19': 'Բարև'}`։

`app/translation.py:173–180` · `translate`

```python
                completed.update(validate_result(json.loads(response.text), target))
                if len(completed) < len(cues):
                    storage.save_cache(partial_key, completed)
                    continue
                result = {str(cue['id']): completed[str(cue['id'])] for cue in cues}
                storage.save_cache(identity, result)
                storage.delete_cache(partial_key)
                return result
```

Գրանցումը կատարվում է ստուգումից հետո։ Թերի արդյունքն անցնում է մասնակի պահոց, իսկ ամբողջ խմբի արդյունքը՝ հիմնական պահոց։ Սխալ հայերեն պարունակող, բայց ճիշտ կառուցվածքով պատասխանից վավեր տողերը նույնպես պահպանվում են։ Կառուցվածքային սխալի դեպքում հաջորդ ուղղման խմբի չափը կիսվում է (`app/translation.py:181–195`)։ Օրինակ՝ մեկ սխալ 24-անոց խմբին կարող են հաջորդել երկու ճիշտ 12-անոց խմբեր (`tests/test_efficient_translation.py:85–98`)։ Նույն կանչում մեկ տողի պատասխանը ստուգելիս առավելագույնը երեք փորձ կա։

`app/main.py:117–124` · `worker`

```python
            except translation.TemporaryTranslationError:
                delay = 60
                job.update(phase='retrying', retry_at=time.monotonic() + delay)
                if job.get('file_identity'):
                    storage.save_file_job(job)
                await asyncio.sleep(delay)
                job.update(phase='translating', retry_at=None)
                continue
```

Արտաքին ծառայության `500`, `502`, `503`, `504` սխալներից `translate`-ը ստեղծում է `TemporaryTranslationError` (`app/translation.py:206–210`)։ `worker`-ը դնում է `retrying` վիճակը, պահում ֆայլի աշխատանքի ընթացքը, սպասում 60 վայրկյան ու վերադառնում նոր շրջանի։ Սա առանձին է մեկ պատասխանի երեք ուղղման փորձերից։ Ծառայության տված `429`-ը բացատրությամբ փոխանցվում է օգտատիրոջը (`app/translation.py:211–214`)։ Սխալի ու նոր փորձի ընթացքում browser-ի ցուցադրած տեքստը գտիր `static/file-translator.js:68–77`-ում։

### Քայլ 4․ պահիր արդյունքը՝ հաջորդ անգամ բացելու համար

Խմբի հաջող արդյունքով `worker`-ն ավելացնում է նոր տողերն ընդհանուր աշխատանքին և ֆայլի համար պահում ընթացքը։ Ավարտին կանչում է `archive_completed_translation` (`app/main.py:125–141`)։ Մի շփոթիր երեք տարբեր հարցերը․ «արդյո՞ք այս խումբն արդեն թարգմանել եմ» պատասխանում է `translations` աղյուսակը, «որտե՞ղ կանգ առավ այս ֆայլը»՝ `file_jobs`-ը, «ի՞նչ պատրաստ արդյունք կարող եմ հիմա ներբեռնել»՝ `subtitle_library`-ն (`app/storage.py:14–18`)։

`app/storage.py:52–58` · `save_file_job`

```python
def save_file_job(job):
    fields = ('filename','original_base64','cues','translated','model','prompt_version','error','error_code','phase',
              'restored_cues','cache_cues','compatible_cache_cues','silent_cues')
    payload = {field:job.get(field) for field in fields}
    with connect() as db:
        db.execute('INSERT INTO file_jobs(id,fingerprint,payload) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=CURRENT_TIMESTAMP',
                   (job['file_identity'], job['file_fingerprint'], json.dumps(payload,ensure_ascii=False)))
```

Աշխատանքի համար գրանցվում են բնագիրը, ժամանակները, արդեն ընդունված տողերը և վիճակը։ Նույն համարով նոր պահպանումը թարմացնում է այդ աշխատանքի տվյալները։ Ֆայլը նորից բացելիս `get_file_job`-ը կարող է վերականգնել դրանք բազայից և կրկին ստուգել (`app/main.py:286–302`)։ Ուստի browser-ի հիշած `id`-ն բավական է նույն աշխատանքին վերադառնալու համար, եթե դրա տվյալները շարունակում են լինել բազայում։ `cancel` գործողությունը դադարեցնում է առաջադրանքը և պահում ֆայլի ընթացքը, իսկ `retry`-ը նույն աշխատանքի համար կանչում է `start` (`app/main.py:272–281,448–452`)։

`app/main.py:498–507` · `archive_completed_translation`

```python
    if any(str(c['id']) not in job['translated'] for c in job['cues']):
        return False
    try:
        for cue in job['cues']:
            if not is_music_only(cue['source']):
                translation.validate_text(job['translated'][str(cue['id'])],cue)
        text=translated_srt(job['cues'],job['translated'])
    except (ValueError,KeyError,TypeError):
        return False
    storage.save_library_translation(job,text)
```

Թերի ֆայլը չի մտնում պատրաստի գրադարան։ Լրիվ ֆայլի համար նախ ստուգվում են խոսք պարունակող տողերը, ապա `translated_srt`-ը պատրաստում է վերջնական SRT-ն։ `save_library_translation`-ը պահում է այն `subtitle_library`-ում և նախորդ գրառումը թարմացնելիս պահպանում օգտատիրոջ ընտրած վերնագիրը (`app/storage.py:90–99`)։ Տեղային մեկ ընդհանուր տեսադարանի կարգավորմամբ `local_library.archive`-ը նաև գրում է `armenian.srt`-ն և սկզբնական ֆայլը (`app/local_library.py:45–66`)։ Մյուս դեպքում սովորական պատճենը գնում է բազայի կողքի `translated-subtitles` պանակ (`app/main.py:508–528`)։

Բնագրի ժամերը մնում են հայերեն տողերի հիմքը։ Արտահանման պահին կա մեկ կարևոր պայման։ Եթե սկզբնական հատվածները ծածկում են միմյանց, հայերեն SRT-ն ստանում է հաջորդական միջակայքներ։

`app/subtitles.py:149–156` · `normalize_timings`

```python
        if merged and start == merged[-1]['start']:
            merged[-1]['source'] += '\n' + cue['source']
            merged[-1]['end'] = max(merged[-1]['end'], end)
        else:
            merged.append(dict(cue))
    for index, cue in enumerate(merged):
        if index + 1 < len(merged):
            cue['end'] = min(cue['end'], merged[index + 1]['start'])
```

Նույն պահին սկսվող տողերը միացվում են տողադարձով ու վերցնում ավելի ուշ վերջը։ Այլ սկիզբ ունեցող յուրաքանչյուր հատվածի պատճենը ներառվում է հերթով, իսկ ավարտը կրճատվում է առավելագույնը մինչև հաջորդ սկիզբը։ `translated_srt`-ը բաց է թողնում միայն երաժշտությունը նշող հատվածները և կառչում `id`-ից՝ յուրաքանչյուր խոսքի հայերենը գտնելու համար (`app/subtitles.py:121–136`)։ Վերջում `render_srt`-ը նորից գրում է հերթական համարները և `ժամ:րոպե:վայրկյան,միլիվայրկյան` գրությամբ պահերը (`app/subtitles.py:109–115,162–165`)։

`tests/test_srt_timing.py:15–20` · `test_overlap_example_keeps_starts_text_and_final_end`

```python
    cues = [cue(1, 35.120, 41), cue(2, 38.120, 43.960), cue(3, 41, 46.520)]
    output = translated_srt(cues, {'1': 'Մեկ', '2': 'Երկու', '3': 'Երեք'})
    parsed = parse_subtitles(output.encode())
    assert [(c['start'], c['end']) for c in parsed] == [(35.120, 38.120), (38.120, 41), (41, 46.520)]
    assert [c['source'] for c in parsed] == ['Մեկ', 'Երկու', 'Երեք']
    assert cues[0]['end'] == 41
```

«Մեկ»-ը սկզբում նախատեսված էր `35.120–41.000` վայրկյանների համար։ «Երկու»-ն սկսվում է `38.120`-ին։ Ներբեռնվող արդյունքը «Մեկ»-ի **վերջը** տեղափոխում է `38.120`, առանց բնագրի առաջին գրառումը փոխելու։ Կոդի նկարագրությունը հիմնավորում է ընտրությունը՝ պահել տեքստը և վերացնել համընկնող միջակայքները (`app/subtitles.py:139–140`)։ Սկզբնական ժամերը բառացի պատճենելը կհեշտացներ արտահանումը, սակայն ցուցադրող ծրագրին կթողներ այդ պահերին միաժամանակ երկու հատված ներկայացնելու խնդիրը։

### Քայլ 5․ տես պատասխանը browser-ում և գտիր կրկնության պատճառը

`static/file-translator.js:89–92` · `poll`

```javascript
    try{
      const state=await request('/api/subtitle-files/'+identity);if(cancelling||identity!==pollingIdentity)return;render(state);
      if(state.running)timer=setTimeout(poll,1000);
    }catch(error){
```

`polling` նշանակում է պարբերաբար հարցնել աշխատանքի ընթացքը։ Browser-ը դիմում է նույն աշխատանքի հասցեին և այն կրկին հարցնում մոտ մեկ վայրկյան անց, եթե դեռ աշխատանք կա։ `file_translation_status`-ը կանչում է `file_status`․ ներբեռնման հասցեն տրվում է միայն պատրաստ ֆայլի համար (`app/main.py:349–352,369,427–429`)։ `render`-ը այդ հասցեն դնում է հղման մեջ, իսկ գրադարանը նորից է կարդում `/api/library`-ն (`static/file-translator.js:60–65`, `static/translation-library.js:93–100`)։ Հղումը սեղմելիս `download_file_translation`-ը գտնում է պատրաստ տեքստը, և `srt_response`-ը վերադարձնում է ներբեռնվող UTF-8 ֆայլը (`app/main.py:464–485`)։

Եթե կարծես թե թարգմանությունը երկու անգամ է պահանջվել, նախ տարբերիր հարցման **հասցեն**։ Պարբերաբար կրկնվող `GET /api/subtitle-files/{identity}`-ը միայն կարդում է վիճակը։ Իսկական արտաքին կանչը `app/translation.py:168`-ում է։ Եթե այն կրկնվել է, հերթով ստուգիր, թե արդյոք `target`-ի համարները տարբեր խմբեր են, տեղի է ունեցել սխալ պատասխանի վերափորձ, թե փոխվել են `cache_key`-ի մուտքերը։ Բացիր `tests/test_cache_resume.py:34–44`․ այնտեղ միաժամանակ միայն մի հատկություն է փոխվում և վերականգնման արդյունքը դատարկ է։ Եթե միայն ֆայլի անունն է փոխվել, `tests/test_cache_resume.py:54–70`-ում նույն աշխատանքը վերականգնվում է։

**Փորձիր ինքդ։** Աշխատանքային պանակը ծրագրի արմատն է։ Առաջին հրամանով գործարկիր մեկ խմբավորման փորձ․ այն կեղծ պատասխան տվող ծրագրով է հաշվում արտաքին կանչերը, ուստի իրական Gemini բանալի կամ ծախս պետք չէ։ Երկրորդով ստուգիր ժամերի վերոհիշյալ օրինակը։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_efficient_translation.py::test_48_cues_use_two_requests_and_reload_uses_none
.\.venv\Scripts\python.exe -m pytest -q tests/test_srt_timing.py::test_overlap_example_keeps_starts_text_and_final_end
```

Սպասիր երկու առանձին `1 passed` արդյունքի։ Առաջինում կարդա `assert len(calls) == 2`-ն երկու անցումից **հետո**։ Երկրորդում վերջին `assert`-ը ստուգում է, որ բնագրի ավարտը մնացել է `41`։

**Արժե առանձին ուսումնասիրել։** Որոնիր `cache invalidation`՝ հասկանալու, թե երբ նախկին հաշվարկն այլևս չի համապատասխանում մուտքին (`app/translation.py:75–96`)։ Ապա՝ `retry and backoff`, որպեսզի կարողանաս տարբերել կրկնվող անհաջող հարցումն ու հաջորդ ծրագրված փորձը (`app/main.py:115–124`)։

<a id="extension"></a>

## 7. Chrome հավելումը․ նույն ենթագիրը ուրիշ կայքի տեսանյութի վրա

Նախորդ քայլերում էջը քոնն էր․ կարող էիր դրա `<video>`-ին ենթագրերի ֆայլ կցել։ YouTube-ում էջն ուրիշինն է։ HaySub-ի `extension`-ը՝ Chrome-ի մեջ տեղադրվող լրացուցիչ ծրագիրը, գտնում է այնտեղ արդեն աշխատող տեսանյութը և վրայից նկարում է իր տեքստը։ Այս շերտն անվանում են `overlay`։ Անցնենք այն ամենակարճ ճանապարհով՝ նախապես պատրաստ ֆայլով։

### Տեղադրիր և կապիր ֆայլը ճիշտ տեսանյութին

Chrome-ում բացիր `chrome://extensions`, միացրու **Developer mode**, ընտրիր **Load unpacked** և ցույց տուր հենց նախագծի `extension` պանակը։ Թարմացրու բաց YouTube էջը։ Բացիր HaySub-ի նշանը, անջատիր «Թարգմանել հայերեն» ընտրությունը, հետո ընտրիր `extension/sample.srt`։ Սա թույլ է տալիս նույն ֆայլով ստուգել ժամացույցը՝ անգամ առանց կազմաձևված թարգմանչի։

**Ո՞ր ծրագիրն է բեռնվում։** `content script`-ը հավելման կոդն է, որ Chrome-ը գործարկում է բաց էջի ներսում։ `popup`-ը նշանը սեղմելիս բացվող կառավարման պատուհանն է։ `service worker`-ը հավելման ֆոնային մասն է, որը ստանում է պատուհանի կամ էջի հաղորդագրությունները և անհրաժեշտության դեպքում դիմում է HaySub-ին։ Chrome-ը դրանց անուններն ու թույլատրված էջերը կարդում է տեղադրման նկարագրությունից։

`extension/manifest.json:13–17` · `content_scripts`

```json
  "content_scripts": [{
    "matches": ["https://www.youtube.com/*", "https://youtube.com/*", "https://m.youtube.com/*"],
    "js": ["core.js", "translation-client.js", "content.js"],
    "run_at": "document_idle",
    "all_frames": false
```

Երեք ծրագրերը բեռնվում են թվարկված հերթով․ սկզբում ենթագրի ընդհանուր գործիքներն են, հետո՝ թարգմանության ընթացքին հետևող մասը, վերջում՝ էջի վրայի տեքստը։ Փոքր պատուհանի ֆայլի ընտրիչը պարունակությունը դարձնում է տեքստ և ստուգում այն։

`extension/popup.js:89–93` · `file դաշտի change գործողություն`

```javascript
      try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}
      catch{throw Error('Ֆայլը պետք է լինի UTF-8 ձևաչափով։ Վերապահպանիր և փորձիր կրկին։');}
      const parsed=C.parse(text);
      await current(); // Do not associate a file with a new video after SPA navigation.
      if(!PUBLIC&&$('translate-enabled').checked){await beginTranslation(text,file.name);return;}
```

`C.parse`-ն այստեղ `extension/core.js`-ի `parse`-ն է։ Ժամերը կարդալուց հետո այն ամեն հատվածի համար կազմում է գրառում։ Դատարկ և զրոյական տևողությամբ հատվածները հաշվում է որպես բաց թողնված․ այդպես, ներքևի օրինակի դատարկ երրորդ հատվածը տեքստ չի դառնում։

`extension/core.js:88–92` · `parse`

```javascript
      const content=plainText(lines.slice(row+1).join('\n'));
      if (!content || end === start) { ignored++; continue; }
      if (content.length > 5000) throw Error(`Հատված ${i+1}․ տեքստը չափազանց երկար է (առավելագույնը՝ 5000 նիշ)։`);
      cues.push({id:cues.length+1,start,end,text:content});
      if (cues.length > 10000) throw Error('Ֆայլը կարող է պարունակել առավելագույնը 10 000 հատված։');
```

Եթե թարգմանությունը միացված է տեղական տարբերակում, `beginTranslation`-ը սկսում է [նախորդ գլխի](#subtitles) աշխատանքը։ Անջատած դեպքում `popup`-ն ֆայլի տեքստը պահում է `chrome.storage.local`-ում՝ հենց այդ Chrome հավելման տվյալների պահոցում։ Բանալին կազմվում է տեսանյութի `id`-ից։ Սա այլ պահոց է, քան Python-ի SQLite բազան։

`extension/popup.js:95–96` · `file դաշտի change գործողություն`

```javascript
      const next={version:1,name:file.name.slice(0,200),text,selectionId:'local:'+Date.now()+':'+Math.random(),updatedAt:Date.now()};
      const key=C.FILE_PREFIX+videoId;
```

`extension/popup.js:99–100` · `file դաշտի change գործողություն`

```javascript
      if(used-old+C.recordBytes(key,next)>C.SAVE_BUDGET)throw Error('Տեղային հիշողությունը լցվել է։ Մաքրիր պահված ենթագրերը և փորձիր կրկին։ Նախորդ ֆայլը պահպանված է։');
      try{await chrome.storage.local.set({[key]:next});}
```

Պահոցի փոփոխությունը հասնում է բաց էջին։ `changed`-ը ստուգում է՝ փոխվե՞լ է հենց ընթացիկ տեսանյութի ֆայլը, դրա շեղումը կամ ցուցադրման կարգավորումը։ Եթե այո, կանչում է `load`-ը։

`extension/content.js:126–126` · `changed`

```javascript
  function changed(changes,area){if(area==='local' && (changes[C.SETTINGS_KEY] || changes[C.FILE_PREFIX+videoId] || changes[C.OFFSET_PREFIX+videoId]))void load();}
```

`extension/content.js:103–107` · `load`

```javascript
      if(next && typeof next.text==='string') {
        if(!record || record.text!==next.text){const parsed=next.text?C.parse(next.text):{cues:[],ignored:0};index=C.timeline(parsed.cues);ignored=parsed.ignored;}
        record=next;
      } else {record=null;index=C.timeline([]);ignored=0;}
      error='';lastText=null;lastGeometry='';sync();
```

`load`-ը կարդացած տեքստից ստանում է հատվածների ցուցակը և տալիս `C.timeline`-ին։ `Timeline`-ն այստեղ ժամանակով դասավորված ցուցակն ու դրա մեջ փնտրելու միջոցն է։ `sync()`-ը խնդրում է անմիջապես ստուգել, թե հիմա ինչ պետք է երևա։ Հիմնական կանչը `render`-ի մեջ է։

`extension/content.js:44–50` · `render`

```javascript
    // No wall-clock extrapolation: buffering, speed changes and seeks use this same clock.
    const active=index.at(video.currentTime,delay);
    const text=active.map(c=>C.withoutMusicLines(c.text)).filter(Boolean).join('\n');
    if(!text){hide();return;}
    if(text!==lastText){caption.textContent=text;lastText=text;lastGeometry='';}
    if(!layout())return;
    host.style.display='block';
```

### Հաշվիր այն պահը, երբ երկու տողերն էլ երևում են

Ահա ֆայլից երկու իրական հատված։ Մեկի վերջը մյուսի սկզբից ուշ է։

`extension/sample.srt:1–9` · `փորձնական ենթագրի սկիզբը`

```srt
1
00:00:01,000 --> 00:00:05,000
Բարև։ Սա HaySub-ի փորձնական ենթագիրն է։
Hello! This is an original test subtitle.

2
00:00:04,000 --> 00:00:07,000
Այս տողը համընկնում է նախորդ հատվածին։
Both cues should be visible at 4 seconds.
```

`video.currentTime`-ը ֆիլմի հենց ներկա ժամանակն է՝ վայրկյաններով։ `index.at`-ը ներսում նրանից հանում է ենթագրի շեղումը։ Ընտրված ժամանակը նշանակենք `t` տառով։ Ընտրության կանոնն է `start ≤ t < end`։

`extension/core.js:106–113` · `timeline.at`

```javascript
      at(seconds, delay=0) {
        const t=Number(seconds)-Number(delay);
        if (!Number.isFinite(t)) return [];
        let lo=0,hi=ordered.length;
        while(lo<hi) { const mid=(lo+hi)>>>1; if(ordered[mid].start<=t)lo=mid+1;else hi=mid; }
        const active=[];
        for(let i=lo-1;i>=0 && maxEnds[i]>t;i--) if(ordered[i].end>t&&!isMusicOnly(ordered[i].text))active.push(ordered[i]);
        return active.reverse();
```

`lo` և `hi` փոփոխականները սահմանում են որոնվող ցուցակի հատվածը։ Կեսից համեմատելով՝ կոդը գտնում է այն սահմանը, որից հետո տողերը դեռ չեն սկսվել։ Ապա հետ է քայլում և հավաքում դեռ չավարտվածները։ `maxEnds`-ը մինչև տվյալ դիրքը հանդիպած ամենաուշ ավարտն է (`extension/core.js:100–104`)․ դրա շնորհիվ երկար հատվածը չի կորչում կարճի տակ։ Եթե շեղումը զրո է, ապա `4.000` վայրկյանին առաջին հատվածի համար `1 ≤ 4 < 5` է, երկրորդի համար՝ `4 ≤ 4 < 7`։ Երկուսն էլ ակտիվ են։ `5.000`-ին մնում է միայն երկրորդը։ `+2` վայրկյան շեղման դեպքում նույն համադրությունը կերևա տեսանյութի `6.000`-ին, քանի որ `6 − 2 = 4`։

Վերադարձիր `render`-ին։ Այն ակտիվ տեքստերը միացնում է նոր տողով, իսկ `caption.textContent=text`-ը բառերը դնում է էջի տարրի մեջ։ `attach`-ը տարրը նախապես կցել է հայտնաբերված նվագարկիչին։ `tick`-ը հաջորդ զննումն է նշանակում այն ժամանակ, երբ տեսանյութը խաղում է և էջը տեսանելի է։

`extension/content.js:81–83` · `attach`

```javascript
    region=document.createElement('div');region.className='region';
    caption=document.createElement('div');caption.className='caption';
    region.append(caption);shadow.append(style,region);container.append(host);
```

`extension/content.js:59–62` · `tick`

```javascript
  function tick() {
    frame=0;render();
    if(video && !video.paused && !video.ended && !document.hidden)frame=requestAnimationFrame(tick);
  }
```

**Ինչո՞ւ վերցնել ֆիլմի ժամացույցը։** `content.js:44`-ի մեկնաբանությունը ուղղակի նշում է սպասման, արագության փոփոխության և ժամանակի վրայով թռչելու դեպքերը։ Այլ լուծում կլիներ Play-ի պահից հաշվել անցած իրական ժամանակը։ Այդ հաշվիչը ևս հեշտ է սկսել, բայց ֆիլմը կարող է կանգնել ներբեռնման համար կամ օգտատերը կարող է հետ գնալ։ Ներկա մոտեցման գործնական գինը `video` տարրը գտնելու և նրա փոփոխություններին հետևելու աշխատանքն է։ Դրա արդյունքը երևում է գործող ստուգման մեջ․

`extension/tests/content.test.cjs:53–58` · `video clock handles pauses…`

```javascript
  h.video.currentTime=4;h.video.fire('seeking');
  assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap');
  h.video.paused=false;h.video.fire('play');assert.equal(h.frames.size,1);
  h.video.playbackRate=2;h.video.fire('ratechange');h.frame();
  assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap'); // no independent advancement
  h.video.fire('waiting');h.frame();assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap');
```

### Երբ տվյալները գալիս են պատրաստի գրադարանից կամ թարգմանչից

Պատուհանի գրադարանում ենթագիր ընտրելիս `popup.js`-ը փոխանցում է գրառման `id`-ն (`extension/popup.js:249–253`)։ Ֆոնային `handle`-ը պահանջում է դրա պատրաստ ֆայլը, ստուգում այն և պահում ընտրված ֆիլմի համար։ Այստեղ և ձեռքով ընտրած ֆայլի դեպքում բաց էջի `load → render` շարունակությունը նույնն է։

`extension/library-background.js:32–35` · `handle`

```javascript
    const response=await request('/api/public/library/'+message.identity+'/download');
    const text=await boundedText(response),parsed=C.parse(text);
    if(!parsed.cues.length)throw Error('Ֆայլում ցուցադրվող ենթագրեր չկան։');
    const record={version:1,name:String(message.title||'HaySub').slice(0,190)+'_hy.srt',text,language:'hy',libraryId:message.identity,selectionId:'library:'+message.identity+':'+Date.now(),updatedAt:Date.now()};
```

`app/public.py:198–204` · `public_download`

```python
@router.get('/api/public/library/{identity}/download')
def public_download(identity: str):
    from app.main import srt_response, library_download_name
    item = storage.library_item(identity)
    if not item or not item['published']:
        raise HTTPException(404, 'Published translation not found.')
    return srt_response(item['srt'], library_download_name(item['title']))
```

Հարցումն ընդունող Python կոդը բազայից գտնում է հենց այդ գրառումը․ ներբեռնումը հասանելի է միայն հրապարակված թարգմանության համար։ Արդյունքը ֆայլի տեքստն է։ `extension/library-background.js:39–42`-ը նախ պահում է նոր ֆայլը և հետո մաքրում հին աշխատանքի նշումը։

Տեղական տարբերակով **նոր թարգմանություն** պատվիրելիս հարցումները շարունակվում են նույնիսկ փոքր պատուհանը փակելուց հետո, քանի դեռ տվյալ տեսանյութի էջը բաց է։ `tick`-ն իր հաղորդագրության հետ տալիս է ֆիլմի դիրքը, իսկ ֆոնային `poll`-ը սերվերից վերցնում է պատրաստ եղած ենթագրերը։ Երկու վայրկյանը ստուգումների ընդմիջումն է, ոչ թե ենթագրի երևալու հաճախությունը։

`extension/translation-client.js:13–16` · `tick`

```javascript
      const stored=await chrome.storage.local.get(C.JOB_PREFIX+id),job=stored[C.JOB_PREFIX+id];
      if(!job?.running||job.cancelled)return;
      const response=await chrome.runtime.sendMessage({type:'HAYSUB_TRANSLATE_POLL',videoId:id,position:Math.max(0,Number(clock())||0)});
      if(response?.ok&&response.running&&version===generation)timer=setTimeout(tick,2000);
```

`extension/background.js:57–60` · `poll`

```javascript
    if(Number.isFinite(position)&&position>=0&&position<=604800){
      await api(path(job,'/position'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seconds:position})});
    }
    const state=await api(path(job,'/translated-subtitles'));
```

`extension/background.js:68–70` · `poll`

```javascript
      const previous=(await chrome.storage.local.get(C.FILE_PREFIX+id))[C.FILE_PREFIX+id];
      const record={version:1,name:previous?.name||id+'_hy.srt',text:C.toSrt(state.cues),selectionId:previous?.selectionId||job.backendId,pendingTranslation:state.running,language:'hy',updatedAt:Date.now()};
      try{await putFile(id,record,next);}
```

`state.cues`-ն արդեն պատրաստ տողերն են։ `toSrt`-ը դրանք դարձնում է SRT տեքստ, և `putFile`-ի գրառումը նույն `changed`-ն է գործարկում։ Տարածման հանրային տարբերակում նոր թարգմանություն սկսելը փակված է `extension/background.js:75–79`-ում։ Պատրաստի հանրային գրադարանից ընտրելու ճանապարհը շարունակում է աշխատել։

**Իսկ եթե կայքը YouTube չէ՞։** `frame`-ն այստեղ մեկ այլ էջ է՝ ներկառուցված հիմնական էջի մեջ։ `page-access.js`-ի `activate`-ը գտնում է ընտրված էջի կամ նրա թույլատրված `frame`-ի `video` տարրերը։ Ընտրության բացակայության դեպքում նախընտրում է խաղացողը, այնուհետև՝ ավելի մեծ մակերես ունեցողը։ `pageKey`-ը տարբերակում է էջի հասցեն, ներքին էջը և ընտրված նվագարկչի համարը։

`extension/page-access.js:19–22` · `activate`

```javascript
    if(!found)throw Error('Չհաջողվեց կարդալ նվագարկիչը։ Կայքը կարող է սահմանափակել հավելման հասանելիությունը։');
    frameUrl=found.url;validUrl(frameUrl);
    if(videoIndex===null)videoIndex=[...found.players].sort((a,b)=>Number(b.playing)-Number(a.playing)||(b.width*b.height-a.width*a.height))[0]?.index||0;
    const key=await C.pageKey(tab.url,frameUrl,videoIndex);
```

`extension/page-access.js:49–51` · `discover`

```javascript
      if(f.frameId===0)continue;
      // Probe only hosts already granted by the user, never request every iframe.
      if(!await chrome.permissions.contains({origins:[new URL(f.url).origin+'/*']}))continue;
```

Կոդի մեկնաբանությունը փաստագրում է ընտրված սահմանը․ ներսում որոնումը կատարվում է այն հասցեներում, որոնց համար օգտատերն արդեն թույլտվություն է տվել։ Բոլոր ներկառուցված էջերին միանգամից հասանելիություն խնդրելը կպարզեցներ որոնումը։ Ընտրված տարբերակում երբեմն օգտատերը պետք է ձեռքով ընտրի նվագարկիչն ու հաստատի նրա հասցեն։ Այս կայքերի համար `background.js:35–39`-ը սպասում է օգտատիրոջ ֆայլին․ YouTube-ի ենթագրերի ինքնաշխատ որոնումն առանձին ճանապարհ է։

**Արժե առանձին ուսումնասիրել — `event driven programming` և `binary search`։** Առաջինը բացատրում է, թե ինչպես է պահոցի փոփոխությունը հանգեցնում էկրանի թարմացման (`content.js`-ի `changed`)։ Երկրորդը՝ ինչպես կարելի է հազարավոր ենթագրերից արագ գտնել ժամանակին համապատասխանող հատվածները (`core.js`-ի `timeline.at`)։

**Փորձիր ինքդ։** Նմուշն ընտրելուց հետո դիր ֆիլմը 4 վայրկյանի վրա և դադարեցրու։ Պետք է երևան և՛ «Բարև։ Սա HaySub-ի փորձնական ենթագիրն է։», և՛ «Այս տողը համընկնում է նախորդ հատվածին։» նախադասությունները՝ իրենց անգլերեն տողերով։ Ավելացրու երկու վայրկյան շեղում և կրկնիր ժամը 6 վայրկյանին։ Հետո նույն սկզբունքը ստուգիր առանց Chrome-ի՝ նախագծի արմատում գործարկելով հետևյալ հրամանը․

```powershell
node --test extension/tests/core.test.cjs extension/tests/content.test.cjs
```

Կտեսնես հաջող ստուգումների ցանկ և վերջում `fail 0`։ Այստեղ կոդը ստանում է կանխորոշված ժամացույց. դրա համար արդյունքը կարելի է վերարտադրել առանց տեսանյութի կամ ցանցի։

<a id="media"></a>

## 8. Ինչպե՞ս է ֆիլմը հայտնվում տեսադարանում

### Ավելացրու արդեն հասանելի ֆիլմի հասցեն

Ենթադրենք՝ տեսանյութն ու հայերեն ենթագիրն արդեն հասանելի են երկու առանձին հասցեներով։ Սեփականատիրոջ էջի `Cloud video` բաժնում լրացնում ես `Video URL` և, ցանկության դեպքում, `Subtitle URL` դաշտերը, ապա սեղմում `Load & Play`։ Ֆիլմի տվյալները բեռնելուց հետո տալիս ես անուն ու սեղմում `Add to page`։ Այս առաջին ճանապարհին HaySub-ին բավական է իմանալ՝ որտեղից կարդալ երկու ֆայլերը։

`static/index.html:32–34` · `watch-url-form`

```html
<label for="watch-video-url">Video URL<input id="watch-video-url" type="url" placeholder="https://?/video.mp4" required></label>
<label for="watch-subtitle-url">Subtitle URL (optional, SRT or VTT)<input id="watch-subtitle-url" type="url" placeholder="https://?/subtitles.vtt"></label>
<button id="watch-url-load" type="submit" class="secondary">Load &amp; Play</button>
```

Առաջին դաշտի `required` հատկությունը պահանջում է տեսանյութի հասցե։ Երկրորդ դաշտը կարելի է դատարկ թողնել։ Հասցեները փորձարկում է քո browser-ը (`static/watch.js:150–165`, `loadDirect`)։ Տվյալները պահելու առանձին գործողությունն է ուղարկում հետևյալ հարցումը։

`static/watch.js:206–208` · `watch-save-form`-ի `submit`

```javascript
      const response=await fetch('/api/owner/media/cloud',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,video_url:selected.videoUrl,subtitle_url:selected.subtitleUrl||null,duration:Number.isFinite(video.duration)&&video.duration>0?video.duration:null})});
      const saved=await response.json();if(!response.ok)throw Error(typeof saved.detail==='string'?saved.detail:'Could not add this video to the page.');
      selected.saved=saved;
```

`POST`-ով browser-ը փոխանցում է վերնագիրը, հասցեները և արդեն հայտնի տևողությունը։ `null` նշանակում է, որ արժեք չկա։ `await`-ը սպասում է պատասխանին ու հետո շարունակում։ `saved`-ը արդեն server-ից եկած գրառումն է՝ իր `id`-ով։

`app/media_api.py:165–168` · `save_cloud_video`

```python
        else:
            identity=uuid4().hex
            connection.execute("INSERT INTO hosted_videos(id,title,size,fingerprint,backend,object_key,part_size,state,published,external_video_url,external_subtitle_url,created,updated,subtitle_height,is_new) VALUES (?,?,0,?,'external',?,1,'ready',1,?,?,?,?,10,1)",
                               (identity,title,hashlib.sha256(video.encode()).hexdigest(),'external/'+identity,video,subtitles,now,now))
```

Սա նոր արտաքին ֆիլմի ճյուղն է։ `uuid4().hex`-ը տալիս է 32 նիշանոց `id`։ `INSERT`-ը SQLite-ի `hosted_videos` աղյուսակում պահում է տող՝ `ready` վիճակով և `published=1` նշումով։ Տեսանյութի պարունակությունից ոչ մի կտոր չկա այդ տողի մեջ։ Նախորդ ճյուղը նույն արտաքին հասցեն գտնելիս թարմացնում է եղած տողը (`app/media_api.py:159–164`)։ Եթե նույն հասցեն արդեն կապված է HaySub-ի կառավարվող ֆիլմին, կոդի մեկնաբանությունը բացատրում է հին `id`-ը պահելու պատճառը՝ պահպանվում են պաստառը և դիտման պատմությունը (`app/media_api.py:145–157`)։ Այլ տարբերակ կլիներ ամեն ավելացման համար նոր քարտ ստեղծել. այդ դեպքում նույն տեսանյութը կարող էր երկու դիտման պատմություն ունենալ։

### Ներմուծիր սկավառակի վրայի ֆիլմը

Երկրորդ ճանապարհը տեղային պանակն է։ Այստեղ պետք է գտնել նոր ֆայլը, սպասել, որ ավարտվի պատճենումը, և գրանցել այն։ `worker`-ը առանձին աշխատող ծրագիր է, որն իր հերթին կատարում է այս գործողությունները, նույնիսկ երբ սեփականատիրոջ էջը փակ է։

`app/media_worker.py:37–41` · `run_once`

```python
def run_once():
    backend=stores.store()
    if isinstance(backend,stores.LocalStore) and os.getenv('HAYSUB_LOCAL_VIDEO_FOLDER'):
        from app.local_videos import scan
        scan()
```

`store()`-ը կարգավորումներից ընտրում է ֆայլերը պահելու եղանակը։ `LocalStore` և `HAYSUB_LOCAL_VIDEO_FOLDER` ունենալիս յուրաքանչյուր շրջանի սկզբում կանչվում է `app/local_videos.py`-ի `scan()`-ը։

`app/local_videos.py:52–56` · `scan`

```python
    for path in sorted(inbox.iterdir())[:200]:
        if path.resolve() in known:continue
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
        stat=path.stat()
        if not stat.st_size or time.time()-stat.st_mtime<3:waiting+=1;continue
```

`path`-ը պանակի հերթական գրառումն է։ Ծրագիրը բաց է թողնում արդեն ճանաչած ուղիները, հղումները, պանակներն ու անընդունելի վերջավորությունները։ Զրոյական չափի կամ վերջին երեք վայրկյանում փոփոխված ֆայլը սպասում է հաջորդ շրջանին։ Հաջորդ տողերը համեմատում են հնարավոր կրկնօրինակները և նոր ֆայլի համար գրում են `state='importing'`։ `finish`-ը սովորական տեղային կառուցվածքում ֆայլը տեղափոխում է կառավարվող տեղը, իսկ երբ ֆայլն արդեն ճիշտ տեղում է, ստուգում և հերթագրում է այն (`app/local_videos.py:58–69,73–97`)։

`flat library` է կոչվում այս ծրագրի այն տարբերակը, որտեղ բոլոր ֆիլմերը միասին են `data/videos/` պանակում։ Այն գործում է միայն `HAYSUB_LOCAL_FLAT_LIBRARY=1`, `HAYSUB_MEDIA_STORAGE=local`, համընկնող `HAYSUB_LIBRARY_ROOT` և `HAYSUB_LOCAL_MEDIA_DIR` պայմաններով, տեղային ռեժիմում (`app/local_library.py:7–11`)։ Ահա մի փոքր փորձ, որն ամրագրում է արդյունքը։

`tests/test_flat_library.py:80–84` · `test_import_keeps_one_file_in_place_and_never_registers_it_twice`

```python
    assert item['object_key']=='videos/Film.mp4' and item['state']=='ready'
    assert (flat/item['object_key']).read_bytes()==b'video'
    assert worker.run_once() is False
    assert len(db.all_videos())==1
    assert list((flat/'videos').iterdir())==[flat/'videos/Film.mp4']
```

Ներմուծված ֆայլն է `videos/Film.mp4`։ Հաջորդ `run_once()`-ին նոր գործ չկա. տվյալների բազայում մեկ ֆիլմ է, պանակում՝ մեկ ֆայլ։ Այս կառուցվածքում հեռացնելիս ֆիլմը տեղափոխվում է `data/bin/`, ենթագրերը մնում են տեղում. նույն անունով ֆայլը `data/videos/` հետ տեղափոխելուց հետո հնարավոր է վերականգնել նույն գրառումը։ Սովորական կառավարվող պահոցում հեռացրած ֆիլմը թաքցվում է և ստանում 24 ժամ անց մաքրվելու վերջնաժամկետ, իսկ արտաքին հասցեն հեռացնելիս ջնջվում է միայն գրառումը։ Ուղղությունը որոշում է `app/media_api.py:403–420`-ի `delete`-ը։ Վերականգնման օրինակները տես `tests/test_flat_library.py:210–232` և `tests/test_hosted_video.py:177–192`։

### Հասկացիր մեծ ֆայլի վերբեռնումը՝ մաս առ մաս

Երրորդ ճանապարհին ֆայլը կա սեփականատիրոջ համակարգչում և պետք է հասնի հեռու պահոց։ Այստեղ տարբերիր գրված հնարավորությունը էկրանի վրա երևացողից։ `static/index.html:29–43`-ի այս տարբերակում կան հասցեով ֆիլմ ավելացնելու դաշտերը։ Տեսանյութի ֆայլ ընտրելու `hosted-upload-form`-ը և պանակը ձեռքով ստուգելու `hosted-scan-folder` կոճակը էջում բացակայում են։ Դրանց համար նախատեսված JavaScript կոդը միանում է, եթե համապատասխան տարրը գոյություն ունի։

`static/media-owner.js:231` · `hosted-upload-form`-ի `submit`

```javascript
  $('hosted-upload-form')?.addEventListener('submit',async event=>{
```

`?.`-ը դադարեցնում է կանչը, եթե տարր չկա։ Վերբեռնման ամբողջ ճանապարհն այս checkout-ում կարող ես անցնել պատրաստի test-ով։ `multipart upload` նշանակում է մեծ ֆայլի բաժանում առանձին համարակալված մասերի։ `S3`-ը պահոցի հետ աշխատելու ծառայություն ու համատեղելի կանոնների հավաքածու է։ Այստեղ մի հատվածի հաստատումից հետո կարելի է շարունակել հաջորդից։

`app/media_api.py:243–245` · `create`

```python
    identity=uuid4().hex;key=stores.key_prefix(identity)+'source.mp4';now=time.time()
    item=dict(id=identity,title=clean_title(body.title),size=body.size,fingerprint=body.fingerprint,backend=backend.identity,object_key=key,part_size=part,state='allocating',created=now,updated=now)
    db.create(item)
```

`POST /api/owner/media`-ն ստանում է անվանումը, չափը և `fingerprint`-ը՝ ֆայլը կրկին ընտրելիս ճանաչելու համար հաշվված արժեքը։ Browser-ը այն հաշվում է անունից, չափից, փոփոխության պահից ու ֆայլի սկզբի և վերջի նմուշներից (`static/media-upload.js:5–10`)։ `key`-ը պահոցում ապագա ֆայլի անունն է։ `db.create`-ը գրանցում է `allocating` վիճակը, ապա պահոցի պատասխանից հետո `create`-ը պահում է վերբեռնման համարը և փոխում վիճակը `uploading`-ի (`app/media_api.py:247–249`)։

`static/media-upload.js:38–44` · `upload`

```javascript
      const blob=file.slice((number-1)*session.part_size,Math.min(number*session.part_size,file.size));
      onPhase(`Վերբեռնվում է ${number} / ${session.part_count} հատվածը`);
      const permission=await api(base+'/part-url',{method:'POST',body:{number}});
      if(signal?.aborted)throw aborted();
      const etag=await sendPart(permission.url,blob,signal,loaded=>onProgress(saved+loaded,file.size));
      if(signal?.aborted)throw aborted();
      await api(base+'/ack',{method:'POST',body:{number,etag}});
```

Օրինակ՝ 130 MiB ֆայլի և կանխադրված 64 MiB մասի դեպքում սպասվում են 64, 64 և 2 MiB հատվածներ. մեկ MiB-ը 1,048,576 byte է (`app/media_store.py:25–30`)։ `slice`-ն ընտրում է տվյալ համարի տիրույթը։ `/part-url`-ը server-ից խնդրում է միայն այս մասի համար ժամանակավոր թույլտվություն։ `sendPart`-ը տվյալներն ուղարկում է ստացած հասցեին։ `ETag`-ը պահոցի վերադարձած նշանն է. `/ack`-ով browser-ն ասում է՝ որ մասի համար ինչ հաստատում է ստացել։

`app/media_store.py:102–103` · `S3Store.part_url`

```python
    def part_url(self,key,upload_id,number,ttl):
        return self.client.generate_presigned_url('upload_part',Params={'Bucket':self.bucket,'Key':key,'UploadId':upload_id,'PartNumber':number},ExpiresIn=ttl,HttpMethod='PUT')
```

`app/media_api.py:280–289`-ի `part_url`-ը ստուգում է համարը և կանչում այս մեթոդը։ `presigned URL` նշանակում է նախապես ստորագրված հասցե. այս դեպքում այն սահմանափակ ժամկետով թույլ է տալիս `PUT`-ով գրել մեկ հատված։ S3 տարբերակում տեսանյութի տվյալները browser-ից ուղիղ գնում են պահոց։ Տեղային փորձերում նույն պայմանավորվածությունը սպասարկում է `/dev-media` (`app/media_api.py:536`)։ Շարունակելիս `resume`-ը վերադարձնում է միայն այն մասերը, որոնց չափն ու `ETag`-ը հաստատվում են թե՛ պահոցի, թե՛ տեղային գրառման մեջ (`app/media_api.py:263–273`)։

`app/media_api.py:309–313` · `complete`

```python
    backend=backend_for(item)
    try:validated_manifest(item,backend)
    except (stores.StorageError,MediaError) as exc:raise HTTPException(409,str(exc)) from None
    if not db.update(identity,states=['uploading'],state='finalizing',error=''):raise HTTPException(409,'Video state changed. Refresh its status.')
    return summary(db.get(identity))
```

Վերջում `upload`-ը կանչում է `/complete` (`static/media-upload.js:47–49`)։ `validated_manifest`-ը նույնացնում է մասերի համարները, չափերը և նշանները (`app/media_worker.py:25–34`)։ Սխալ համադրության դեպքում պատասխանը `409` է՝ տվյալների ներկա վիճակը չի թույլ տալիս ավարտել գործողությունը։ Հաջողության դեպքում գրառումը դառնում է `finalizing`։ Այս պահին ֆայլը դեռ պետք է հավաքել և ստուգել։

`app/media_worker.py:71–76` · `run_once`

```python
            if not head:
                manifest=validated_manifest(item,backend)
                backend.complete(item['object_key'],item['upload_id'],manifest)
                head=backend.head(item['object_key'])
            if not head or head['size']!=item['size']:raise MediaError('Completed object size does not match the declared upload. Delete this video and upload again.')
            if not db.update(identity,states=['finalizing'],token=token,state='processing'):return True
```

`worker`-ը ընտրում է հերթում եղած գրառումը։ Եթե վերջնական ֆայլը չկա, պահոցին տալիս է ստուգված մասերի ցանկը և նորից հարցնում վերջնական չափը։ Չափերը համընկնելու դեպքում գրառումը դառնում է `processing`։ Այս հերթականությունը թույլ է տալիս վերսկսել նույնիսկ այն դեպքում, երբ ֆայլն արդեն հավաքված է, բայց ծրագիրն ընդհատվել է մինչ վիճակը թարմացնելը (`tests/test_hosted_video.py:328–334`)։

`app/media_worker.py:79–81` · `run_once`

```python
        info=inspect_media(backend,item['object_key'],item['size'])
        item=local_library.place_video(db.get(identity),backend)
        db.update(identity,states=['processing'],token=token,state='ready',duration=info['duration'],media_info=json.dumps(info),error='',failures=0)
```

`inspect_media`-ն ստուգում է MP4 կառուցվածքը և `ffprobe` ծրագրով կարդում ֆայլի տեխնիկական նկարագրությունը։ `codec`-ը պատկերը կամ ձայնը ներկայացնելու և կարդալու եղանակն է։ Օրինակ՝ `validate_probe`-ը ընդունում է համապատասխան H.264 պատկեր, իսկ առկա ձայնի դեպքում պահանջում է AAC-LC (`app/media_formats.py:106–119`)։

`app/media_formats.py:110–112` · `validate_probe`

```python
    video=videos[0]
    if video.get('codec_name')!='h264' or video.get('pix_fmt')!='yuv420p' or video.get('profile') not in ('Baseline','Constrained Baseline','Main','High') or video.get('level',999)>42:
        raise MediaError('For this release use H.264 8-bit yuv420p, Baseline/Main/High profile, level 4.2 or lower. HEVC, 10-bit and other codecs are not supported.')
```

Այդ ստուգման արդյունքից `worker`-ը պահում է տևողությունն ու այլ հատկանիշները և սահմանում `ready`։ Անհամատեղելի ֆայլի դեպքում այն գրանցում է սխալ և `published=0` (`app/media_worker.py:82–88`)։ `docs/VIDEO_HOSTING.md`-ի «Supported media» բաժինը նկարագրում է ընտրված պայմանը՝ ստուգված ֆայլը ցուցադրել եղած ձևով։ Այլ մոտեցում կլիներ յուրաքանչյուր ֆիլմը նորից կոդավորել. ավելի շատ ձևաչափեր կհաջողվեր ընդունել, բայց դիմացը պետք կլինեին հաշվարկային ժամանակ ու տարածք։

### Կցիր հայերենը և բացիր դիտման հասանելիությունը

`ready` վիճակն ասում է, որ ֆիլմը պատրաստ է։ Սեփականատիրոջ էջի քարտում, երբ ֆիլմը պատրաստ է ու դեռ ենթագիր չունի, երևում է պահպանված թարգմանության ընտրությունը (`static/media-owner.js:65–76`)։

`static/media-owner.js:177–178` · `card`, ենթագրի ընտրության `submit`

```javascript
        const body=new FormData();body.append('library_id',subtitleSelect.value);body.append('offset',String(row.item.subtitle_offset||0));
        const saved=await api('/api/owner/media/'+item.id+'/subtitles',{method:'POST',body});
```

`FormData`-ն browser-ում դաշտերով հարցում կազմելու միջոց է։ Ընտրության `id`-ն ու ֆիլմի ժամանակային շեղումը գնում են `attach`-ին։ Այդ նույն հասցեն կարող է ընդունել նաև պատրաստ հայերեն SRT կամ VTT ֆայլ՝ `subtitles` դաշտով (`app/media_api.py:336–348`)։

`app/media_api.py:349–352` · `attach`

```python
        elif library_id:
            source=storage.library_item(library_id)
            if not source:raise HTTPException(404,'Library subtitle not found.')
            cues=prepared_cues(source['srt'].encode('utf-8'))
```

`storage.library_item`-ը վերադարձնում է ընտրված թարգմանության տողը (`app/storage.py`)։ `prepared_cues`-ը այն բաժանում է ժամանակով մասերի և մաքրում միայն երաժշտություն նկարագրող տողերը (`app/media_formats.py:21–30`)։ `attach`-ը `webvtt(cues,offset)`-ով ստանում է ցուցադրման տեքստը (`app/media_api.py:356`)։ Արտաքին ֆիլմին կցելիս այն պահում է ժամանակներով հատվածներն ու շեղումը SQLite-ում, սովորական պահոցում՝ առանձին VTT, իսկ `flat library`-ում՝ `armenian.srt`։ Վերջին դեպքում VTT տրվում է հարցման պահին (`app/media_api.py:358–374,477–493`)։ Այս գործողությունը վերցնում է արդեն հայերեն նյութը, ուստի թարգմանություն պատվիրելու քայլ չկա։

`app/media_api.py:329–331` · `change`

```python
    if body.published is not None:
        if body.published and (item['state']!='ready' or (not item['subtitle_key'] and not item['external_subtitle_url'] and not item['external_video_url'])):raise HTTPException(409,'Wait for successful media inspection and attach Armenian subtitles before publishing.')
        values['published']=int(body.published)
```

Քարտի հրապարակման կոճակը ուղարկում է `published` դաշտով `PATCH`՝ եղած տողի մասնակի փոփոխության հարցում (`static/media-owner.js:154`)։ Պայմանից հետևում է՝ կառավարվող տեսանյութի համար պետք են `ready` և կցված ենթագիր։ `external_video_url` ունեցող գրառումը կարող է հրապարակվել նաև առանց ենթագրի։ Դրանից հետո դիտողի հանրային ցանկը գտնում է `published` ու `ready` տողը և կազմում `/watch/` հասցեն (`app/media_api.py:175–182`)։

**Արժե առանձին ուսումնասիրել** — `resumable multipart upload` և `state machine`։ Առաջինը բացատրում է՝ ինչպե՞ս շարունակել վերջին հաստատված մասից։ Երկրորդը սովորեցնում է խնդիրը բաժանել վիճակների ու թույլատրելի անցումների. օրինակ՝ `uploading → finalizing → processing → ready`։ Վերադարձիր `static/media-upload.js:27–49` և `app/media_worker.py:69–81`։

**Փորձիր ինքդ։** Նախագծի արմատում PowerShell-ից գործարկիր հետևյալ հրամանը։ Այն իրականացնում է վերբեռնումը, նախադիտումը և հրապարակումը ժամանակավոր պանակում։ Փորձի MP4-ը արհեստական տվյալ է, իսկ `ffprobe`-ի պատասխանը փոխարինված է նախապես հայտնի արժեքով (`tests/test_hosted_video.py:13–18,22–30`)։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_hosted_video.py::test_local_resumable_upload_completion_range_preview_publish_and_delete
```

Ակնկալիր `1 passed`։ Բացիր նույն test-ի 74–87 տողերը. փորձիր նախապես ասել՝ առանց կցված ենթագրի որ հարցումը կստանա `409`, և որ հաջորդ հարցումն արդեն կստանա `200`։

<a id="publish"></a>

## 9. Ինչպե՞ս է տեղային գրառումը հասնում հրապարակային կայք

### Ո՞վ կարող է փոփոխել գրադարանը

`deployment` է կոչվում ծրագրի այն տարբերակի տեղադրումը, որին օգտվողները կարող են միանալ իրենց համակարգիչներից։ HaySub-ի ամբողջական ծառայության դեպքում նույն հասցեի տակ գործում են թե՛ դիտողի կատալոգը, թե՛ սեփականատիրոջ գործիքները։ `middleware`-ը հարցման ճանապարհին աշխատող միջանկյալ կոդ է. այն կարող է վերադարձնել պատասխան դեռ մինչև կոնկրետ գործողությանը հասնելը։

`app/main.py:52–54` · ծրագրի կարգավորում

```python
app.middleware('http')(public.access_control)
app.include_router(public.router)
app.include_router(media_api.router)
```

Առաջին տողն ամեն HTTP հարցում տալիս է `public.access_control`-ին։ Վերջին երկուսը գրանցում են `public` և `media_api` ֆայլերի հասցեները։ `access_control`-ը ներսից կանչում է `controlled_response` (`app/public.py:53–55`)։

`app/public.py:73–76` · `controlled_response`

```python
        public_read = public_read or (request.method in ('GET','HEAD') and (path=='/api/public/videos' or bool(re.fullmatch(r'/api/public/hosted/[a-f0-9]{32}/(?:playback|subtitles\.vtt|poster)',path))))
        login = path == '/api/admin/login' and request.method == 'POST'
        if path.startswith('/api/') and not public_read and not login and not authenticated(request):
            return JSONResponse({'detail':'Owner sign-in required.'}, status_code=401)
```

`HAYSUB_PUBLIC=1` ռեժիմում դիտողը կարող է կարդալ դիտման համար նախատեսված հանրային հասցեները։ Մնացած API հարցումների համար պահանջվում է սեփականատիրոջ մուտք. առանց դրա պատասխանը `401` է։ Օրինակ՝ այցելուն կարող է ստանալ `/api/public/videos`, իսկ `POST /api/owner/media/cloud`-ով նոր ֆիլմ ավելացնելու փորձը մերժվում է։ Փոփոխությունների համար հաջորդ տողերը ստուգում են նաև հարցումը նախաձեռնած կայքի հասցեն (`app/public.py:77–81`)։

`app/public.py:108–111` · `login`

```python
    value = str(int(time.time())+21600)+'.'+secrets.token_hex(16)
    response = JSONResponse({'ok':True})
    response.set_cookie(COOKIE, value+'.'+signature(value), max_age=21600, httponly=True, secure=True, samesite='strict', path='/')
    return response
```

Սեփականատիրոջ գաղտնաբառի հաջող ստուգումից հետո `cookie` է տրվում՝ փոքր արժեք, որը browser-ը պահում և նույն կայքին վերադարձնում է հաջորդ հարցումների հետ։ `21600` վայրկյանը վեց ժամ է։ `signature(value)` ստորագրությունը թույլ է տալիս ստուգել, որ ժամկետը և պատահական հատվածը չեն փոխվել (`app/public.py:38–49`)։ `/admin`-ը բացում է աշխատանքային էջը կամ մուտքի ձևը՝ ըստ այս ստուգման (`app/public.py:121–123`)։ Տեղային ռեժիմում սեփականատերը համարվում է մուտք գործած։ Պատճառը կարդացվում է կոդից. դիտողին կարելի է տալ պատրաստ ֆիլմը՝ առանց ֆիլմեր փոխելու կամ վճարովի թարգմանություններ սկսելու հնարավորություն տալու։ Այլ տարբերակ կլիներ դիտողների համար էլ հաշիվներ ստեղծել։ Այս լուծմամբ պատրաստ ֆիլմը բացելու համար հաշվառման քայլ չկա։

### Ամբողջական ծառայությունը Render-ում

`Docker`-ը ծրագրի ու նրա կախվածությունների համար միասնական գործարկման միջավայր է ստեղծում։ `Dockerfile:1–10`-ը որպես հիմք վերցնում է `python:3.13-slim`-ը, տեղադրում FFmpeg-ը և `requirements.lock.txt`-ի ճշգրիտ տարբերակները, հետո պատճենում `app/` ու `static/` պանակները։

`Dockerfile:12–15` · գործարկման հրահանգ

```dockerfile
# One process: SQLite and in-process owner translation jobs must share state.
# The entry point initializes disk ownership, then drops to the haysub user
# before importing the web app or accepting any requests.
CMD ["python", "-m", "app.serve"]
```

`CMD`-ից կատարումը տեղափոխվում է `app/serve.py`-ի `main`։ Ֆայլի մեկնաբանությունը բացատրում է, թե ինչու ընտրվել է մեկ վեբ գործընթաց. SQLite-ն ու հիշողության մեջ պահվող թարգմանության աշխատանքները պետք է համատեղելի վիճակ տեսնեն։ Մի քանի վեբ գործընթաց ունենալու դեպքում ընթացիկ աշխատանքի տվյալները նույնպես պիտի հասանելի լինեին բոլորին։

`app/serve.py:35–37` · `main`

```python
    if os.getenv('HAYSUB_MEDIA_WORKER_ENABLED')=='1' and os.getenv('HAYSUB_MEDIA_STORAGE'):
        threading.Thread(target=supervise,daemon=True).start()
    try:uvicorn.run('app.main:app', host='0.0.0.0' if os.getenv('HAYSUB_PUBLIC')=='1' else '127.0.0.1', port=int(os.getenv('PORT','8000')), workers=1,access_log=False)
```

Պահոցը կարգավորված լինելու և `HAYSUB_MEDIA_WORKER_ENABLED=1` պայմանների դեպքում վերահսկող գործառույթը առանձին գործընթացում կանչում է `python -m app.media_worker` (`app/serve.py:24–28`)։ Իսկ `uvicorn.run`-ը հանրային ռեժիմում լսում է `0.0.0.0`-ի վրա՝ հարթակից ստացած `PORT` համարով։

`render.yaml:6–10` · `services[0]`

```yaml
    healthCheckPath: /healthz
    disk:
      name: haysub-data
      mountPath: /var/data
      sizeGB: 1
```

`Render`-ի այս կարգավորումը նախատեսված է Docker-ով աշխատող վեբ ծառայության համար։ `persistent disk`-ը վերագործարկումից հետո ֆայլերը պահպանող սկավառակն է. այստեղ այն միացված է `/var/data`-ին, և նույն ֆայլի 14–15 տողերում `HAYSUB_DB`-ն ուղղված է `/var/data/haysub.sqlite3`։ `/healthz` պարբերական հարցմամբ հարթակը ստուգում է՝ հասանելի՞ է ծրագիրն ու բազան։

`app/public.py:126–130` · `health`

```python
@router.get('/healthz')
def health():
    with storage.connect() as db:
        db.execute('SELECT 1')
    return {'status':'ok'}
```

`SELECT 1`-ը բազային ուղղված ամենափոքր փորձնական ընթերցումներից է։ Հաջողության ժամանակ պատասխանն է `{"status":"ok"}`։ Հանրային գործարկման սկզբում `validate_configuration`-ը պահանջում է առնվազն 32 նիշանոց `HAYSUB_ADMIN_TOKEN` և կայքի HTTPS հասցե (`app/public.py:29–35`)։ Տեսանյութ պահելու համար առանձին են կարգավորվում S3 պահոցն ու մուտքի տվյալները (`app/media_store.py:41–48,64–69`)։ `.env.example`-ում նշված են փոփոխականների անունները, `docs/VIDEO_HOSTING.md`-ում՝ տեղադրման մանրամասները։

### Երբ դիտողի կայքը բաղկացած է պատրաստի ֆայլերից

Մյուս ճանապարհին ֆիլմերը հրապարակելուց առաջ կառուցում ես `manifest`՝ ցանկը նկարագրող փոքր ֆայլ։ HaySub-ում դա `catalog-site/catalog.json`-ն է։ Դիտողի ամպային կայքը կարող է սպասարկել այդ ֆայլը, նկարները և էջերը։ Ամեն բացման ժամանակ Python և սեփականատիրոջ տվյալների բազա հասանելի դարձնելու կարիք չկա։

`app/catalog_sync.py:19–20` · `enabled`

```python
def enabled():
    return os.getenv('HAYSUB_PUBLIC') != '1' and os.getenv('HAYSUB_STATIC_CATALOG_SYNC') == '1'
```

Տեղային գործարկման սկզբում (`app/main.py:44`), սեփականատիրոջ հաջող փոփոխությունից կամ տեսանյութերի ցանկի թարմացումից հետո (`app/media_api.py:37–49`) կանչվում է `sync`։ Այն աշխատում է միայն տեղային ռեժիմում և `HAYSUB_STATIC_CATALOG_SYNC=1` դեպքում։

`app/catalog_sync.py:48–52` · `sync`

```python
            if marker == _fingerprint and (target / 'catalog.json').exists():
                return _status['state']
            data, skipped = export_library(storage.DB, config, target, strict=False)
            save_manifest(target, data)
            _fingerprint = marker
```

`marker`-ում ամփոփված են գրառումների վիճակը, ընտրված պահոցը և կարգավորումները։ Եթե նույն տեղեկության համար ֆայլն արդեն կա, վերադարձվում է նախորդ արդյունքը։ Փոփոխության դեպքում `export_library`-ն վերցնում է տվյալները SQLite-ից։ `save_manifest`-ը նոր արդյունքը գրում է ֆայլի մեջ։

`app/catalog_export.py:87–90` · `export_library`

```python
        rows = db.execute("SELECT * FROM hosted_videos WHERE state='ready' AND (published=1 OR published_at IS NOT NULL) ORDER BY COALESCE(published_at,created) DESC").fetchall()
        for raw in rows:
            row = dict(raw)
            visible = bool(row['published']) and not (row['id'] in hidden and not row.get('list_restored'))
```

`SELECT`-ը փնտրում է պատրաստ և այժմ կամ նախկինում հրապարակված տողերը։ `visible`-ը հաշվի է առնում նաև ցանկից թաքցնելու կարգավորումը։ Հաջորդ տողերը բաց են թողնում միայն տեղային հասցե ունեցող ֆիլմերը, եթե դրանց համար ամպային մատուցում ընտրված չէ (`app/catalog_export.py:93–96`)։

`app/catalog_export.py:98–103` · `export_library`

```python
                film = {'id': row['id'], 'title': row['title'], 'published': visible,
                        'video_url': external or cloud(row['object_key']),
                        'subtitle_url': row.get('external_subtitle_url') or cloud(row.get('subtitle_key')),
                        'subtitle_offset': row.get('subtitle_offset') or 0,
                        'subtitle_height': row.get('subtitle_height', 10), 'is_new': bool(row.get('is_new', False))}
                validate({'version': 1, 'films': [film]})
```

Յուրաքանչյուր ֆիլմի գրառում պարունակում է վերնագիրը, հասանելիության նշումը, տեսանյութի ու ենթագրի հասցեները, ժամանակային շեղումն ու ենթագրի բարձրությունը։ Արտաքին հասցեի բացակայության դեպքում `cloud`-ը հասցե է կազմում կարգավորված հիմքից և պահոցի բանալիից։ `validate`-ը պահանջում է մշտական, հանրային HTTPS հասցեներ (`app/catalog_export.py:13–25,44–47`)։ Կարևոր հետևանք. `published: false` ունեցող գրառումը կարող է մնալ հանրային JSON-ում. այն ցուցակից թաքցնելը չի փակում արդեն հայտնի հանրային մեդիայի հասցեն։

`app/catalog_export.py:130–133` · `save_manifest`

```python
def save_manifest(destination, data):
    """Replace JSON last, then remove only our obsolete generated cover files."""
    destination = Path(destination)
    atomic_write(destination / 'catalog.json', (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
```

`ensure_ascii=False`-ի շնորհիվ հայերենը ֆայլում ընթեռնելի է։ `atomic_write`-ը գրում է ժամանակավոր ֆայլ ու պատրաստ լինելուց հետո մեկ գործողությամբ փոխարինում հինը (`app/catalog_export.py:63–67`)։ Այս կերպ դիտողը չի ստանում կիսագրված JSON։ Հանրայնացվող պաստառները նախապես գրվում են նկարից հաշվված անուններով (`app/catalog_export.py:113–126`)։ Առանցքային տարբերությունը նկարագրում է `app/catalog_sync.py:1–4`-ի մեկնաբանությունը. այս տեղային գործողությունը ստեղծում է կայքի ֆայլերը։ Այցելուն փոփոխությունը տեսնելու համար դրանք դեռ պետք է ներառել Git փոփոխության մեջ և տեղադրել կայքում։ Տեսանյութերն ու ենթագրերն իրենց հանրային հասցեներում արդեն պետք է հասանելի լինեն։

`docs/STATIC_CATALOG.md:14–25`-ում նախագծի համար նկարագրված է Render-ի առանձին `Static Site`. հրամանի աշխատանքային պանակը նախագծի արմատն է, `Build Command`-ը՝ `node catalog-site/build.cjs`, հրապարակվող պանակը՝ `catalog-site`։ Ահա կոնկրետ ինչ է անում այդ հրամանը։

`catalog-site/build.cjs:3–5` · ֆայլի հիմնական կոդ

```javascript
const metadata={updated_at:new Date().toISOString()};
fs.writeFileSync(path.join(__dirname,'deployment.json'),JSON.stringify(metadata)+'\n');
console.log('Updated deployment date.');
```

`Node.js`-ը տվյալ պահին համակարգչի ժամով հաշվում է պահը և ստանդարտ գրությամբ գրում `deployment.json`-ում։ Հաջողության դեպքում գրվում է `Updated deployment date.`։ Էջը կարդում և Երևանի ժամով է ցուցադրում այդ արժեքը (`catalog-site/deployment-date.js:7–13`)։ Սա տեղադրման պահն է, ուստի երկու այցելուներին տարբեր օրերի բացելիս կարող է երևալ նույն ամսաթիվը։ Հասանելի Git պատմության մեջ `52231df`-ը ավելացրել է `catalog_export.py` և `catalog_sync.py` ֆայլերը, իսկ `aaaa301`-ը՝ `catalog-site/build.cjs`-ը։ Render-ի ամբողջական ծառայության կարգավորումը կար արդեն `6292363`-ում։ Այստեղ նշված են repository-ի փաստագրված կարգավորումները. որևէ գործող կայքի ընթացիկ կարգավիճակ դրանցից եզրակացնել հնարավոր չէ։

Եթե հավաքում ես տեղային տարածման փաթեթ, `scripts/build_static_catalog.py:43–65`-ի `main`-ը ստուգում է ցուցակը, `static/`-ից պատճենում ընդհանուր ֆայլերը և ստեղծում `dist/haysub-static-catalog.zip`։ `--export-local` ընտրությունը նաև վերակառուցում է ցուցակը տեղային տվյալներից։ Ամբողջական server-ի և Chrome-ի տարածման փաթեթների համար նախատեսված է այլ գործիք՝ `scripts/build_release.py:107–126`։ Երկուսը տարբեր նպատակ ունեն. օրինակ՝ միայն ֆիլմերի հանրային ցանկը փոխելու համար Gemini-ի տվյալներ ամպային կայքում լրացնելու քայլ չկա։

**Արժե առանձին ուսումնասիրել** — `static site deployment` և `CORS`։ Առաջինն օգնում է հասկանալ, թե կայքի որ տվյալներն են պատրաստվել նախապես։ Երկրորդը browser-ի կանոն է, որով մեկ կայքը կարող է թույլ տալ մեկ այլ կայքի կարդալ իր պատասխանը։ Երբ էջը Render-ում է, իսկ SRT-ն առանձին R2 պահոցում, էջի հասցեն պետք է թույլատրված լինի այդ պահոցի կարգավորումներում։ Ուսումնասիրիր `docs/STATIC_CATALOG.md:23–29` և `docs/storage-cors.example.json`։

**Փորձիր ինքդ։** Նախագծի արմատում PowerShell-ից գործարկիր հետևյալ test-ը։ Այն ժամանակավոր SQLite ֆայլից և ժամանակավոր կայքի պանակից օգտվելով ստուգում է `Add to page`, վերանվանելու, պաստառի և հրապարակումից հանելու արդյունքները։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_catalog_sync.py::test_owner_actions_sync_listings_titles_and_versioned_covers
```

Ակնկալիր `1 passed`։ Կարդա `tests/test_catalog_sync.py:58–65`. հրատարակումից հանելուց հետո ցանկում մեկ թաքցված գրառում կա, իսկ արտաքին ֆիլմի գրառումը ջնջելուց հետո՝ զրո։ Թղթի վրա նկարիր երեք սյունակ՝ SQLite-ի տողը, տեղային `catalog.json`-ը և արդեն տեղադրված կայքը։ Նշիր, թե մեկ վերանվանումից հետո որ երկուսն են թարմանում անմիջապես, երբ sync-ը միացված է, և որը սպասում է հաջորդ տեղադրմանը։

<a id="roadmap"></a>

## 10. Ինքնուրույն աշխատանքի հերթականությունը

| Հերթ | Սովորիր և արա | Երբ անցնել հաջորդ քայլին |
|---|---|---|
| 1 | Բացիր ֆիլմերի պատրաստի ցանկը։ `DevTools → Network`-ում գտիր `catalog.json`-ը, բացիր քարտը, համեմատիր երկու էջերի հասցեները։ | Կարող ես բացատրել `id`-ի դերը և ասել՝ ով է պահում ֆիլմը, ով է բեռնում ենթագիրը։ |
| 2 | Թղթի վրա գրիր երկու ենթագիր՝ մասամբ համընկնող ժամերով։ Փորձիր `offset=+2`, հետո `offset=-2`։ Ստուգիր `extension/core.js`-ի `timeline.at`-ով կամ գլխի պատրաստի ստուգումներով։ | Առանց ծրագրի կանխատեսում ես ակտիվ տողը հենց մեկնարկին, ավարտին և հետ անցնելուց հետո։ |
| 3 | `tests/sample.srt`-ի առաջին գրառմանը հետևիր մինչև `parse_subtitles` և `translated_srt`։ Թղթի մեկ կողմում գրիր սկզբնական ժամերն ու բառերը, մյուսում՝ `id`, `start`, `end`, `source`։ | Բառերով կարող ես տարբերել ընթերցումը, թարգմանությունը և ֆայլը նորից գրելը։ |
| 4 | Կարդա հաջող ու ձախողված մեկական գործ `tests/test_cache_resume.py` և `tests/test_id_recovery.py` ֆայլերում։ Դրանց կողքին բացիր `translate`-ը։ | Կարող ես կանխատեսել՝ որտեղից է գալիս հաջորդ արդյունքը և երբ է ծրագիրը դիմելու Gemini-ին։ |
| 5 | Ընտրիր մեկ պատրաստի ֆիլմ։ Համեմատի՛ր դրա հասցեները սեփականատիրոջ բազայի, հանրային պատասխանի և կայքի `catalog.json`-ի միջև։ Դատարկ գրադարանի դեպքում օգտագործիր `tests/test_catalog_sync.py`-ի փորձնական տվյալները։ | Կարող ես ցույց տալ այն սահմանը, որից հետո դիտողին պետք են միայն հրապարակված ֆայլերը։ |
| 6 | Առանձին ուսումնական պանակում պատրաստիր սեփական մեկ ֆիլմով էջ։ Սկզբում՝ `<video>` և մեկ պատրաստի `<track>`, հետո ավելացրու ֆիլմերի ցանկ, ապա՝ քո ընթերցած ձևաչափից ենթագիր կառուցող փոքր ծրագիր։ | Կարող ես նույն նյութը դիտել, փոխել մեկ տողի ժամը և կանխատեսել արդյունքը։ Միայն այսքանից հետո ավելացրու պահպանում կամ ինքնաշխատ թարգմանություն։ |

### Կարդա նաև մեկ իրական ձախողում

Այս տարբերակի մաքուր պատճենում գործարկված Python-ի ստուգումներից **291-ն անցան, մեկը ձախողվեց**։ Սա դիտելու հարմար առիթ է, թե ինչու են ծրագիրն ու դրա ակնկալվող վարքը կարդում կողք կողքի։ Տեղական ֆիլմ կա՝ `Film.mp4`։ Բոլոր ֆիլմերի համար միացված է հեռակա աղբյուրի ընտրությունը (`HAYSUB_CLOUD_VIDEO_IDS='*'`)։ Ֆայլը վերանվանվում է `Renamed.mp4`, պանակը նորից ստուգվում է, և նոր վերնագրով գրառում է ստեղծվում։

`tests/test_flat_library.py:90–96` · `test_renamed_local_file_does_not_leave_a_second_visible_card`

```python
    monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS','*')
    (flat/original['object_key']).rename(flat/'videos/Renamed.mp4')
    os.utime(flat/'videos/Renamed.mp4',(time.time()-10,time.time()-10))
    with TestClient(main.app) as client:
        assert client.post('/api/owner/media/scan-local').json()['added']==1
        assert worker.run_once()
        assert len(client.get('/api/owner/media').json())==1
```

`assert`-ը ծրագրով ձևակերպված ակնկալիք է։ Վերջին տողում ստուգումը սպասում է մեկ քարտի, իսկ իրական պատասխանում կան երկուսը՝ `Film` և `Renamed`։ Դիտարկումը կարելի է կրկնել առանց սեփական ֆիլմի կամ բազայի փոփոխության։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_flat_library.py::test_renamed_local_file_does_not_leave_a_second_visible_card
```

Հետաքննությունն սկսիր ցուցակը վերադարձնող `owner_list`-ից (`app/media_api.py:110–111`) և անցիր դրա կանչած `listed_videos`-ին։

`app/media_api.py:99–107` · `listed_videos`

```python
def listed_videos():
    items=[item for item in db.all_videos() if not media_sources.hidden_from_lists(item['id'])]
    if os.getenv('HAYSUB_MEDIA_STORAGE')!='local':return items
    backend=stores.store()
    return [item for item in items if not (
        item['backend']==backend.identity and item['state']=='ready'
        and not item['external_video_url']
        and not media_sources.cloud_selected(item['id'])
        and not backend.path(item['object_key']).is_file())]
```

Այս զտիչը բացակայող տեղական ֆայլով գրառումը թաքցնում է, երբ ներսի բոլոր պայմանները միասին ճիշտ են։ Բոլոր ֆիլմերի համար հեռակա աղբյուր ընտրելը նշանակում է, որ `not media_sources.cloud_selected(item['id'])` պայմանը կեղծ է։ Հին քարտը շարունակում է երևալ։ Համեմատիր `tests/test_cloud_links.py:46`-ի `test_cloud_selected_video_stays_listed_without_local_file` փորձի հետ․ սովորական հեռակա դիտման համար նախագծում ակնկալվում է պահել բացակայող տեղական բնօրինակով ֆիլմը։ Այս երկու ստուգումները նկարագրում են երկու տարբեր օգտատիրական դեպք։

### Ստուգումների սահմանները

Ստորև հրամաններն ամփոփում են Python և JavaScript մասերի ստուգումները։ Առաջինը բացահայտում է նաև վերևի ձախողումը։ Երկրորդով այս տարբերակի **154 ստուգումներն անցան**։ Ուղեցույցը կազմելիս մաքուր պատճենում փորձարկվել է նաև իրական տեղական մեկնարկը՝ `start.py`, `/`, `/healthz`, `/catalog` և առանձին պատրաստի կայքի էջերն ու հինգ ֆիլմերի ցանկը։ Թարգմանության ստուգումները օգտագործում են նախապատրաստված պատասխաններ։ Արտաքին Gemini հարցում, ֆիլմերի հեռակա հղումների այսօրվա հասանելիություն և հրապարակային տեղադրում այս թվերով չեն ստուգվում։

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
node --test tests/*.test.cjs extension/tests/*.test.cjs
```

**Արժե առանձին ուսումնասիրել — `regression test`։** Սա ստուգում է, որ նախկինում սպասվող վարքը փոփոխությունից հետո ևս պահպանվի։ Վերադարձիր հենց վերանվանման փորձին․ կարող ես կարդալ անունը, մուտքը և վերջին `assert`-ը՝ դեռ առանց իրականացման մանրամասներն իմանալու։

**Փորձիր ինքդ։** Փակիր կոդը և մեկ րոպեում բացատրիր «22 Փամփուշտ»-ի տողի ճանապարհը մեկ ուրիշին։ Ասա՝ որտեղ է գրված ֆիլմի `id`-ն, որտեղից են գալիս հայերեն բառերը, որ պահին են հաշվվում ժամերը և ում ժամացույցն է որոշում՝ երբ ցուցադրել տողը։ Հետո յուրաքանչյուր պատասխանի համար գտիր մեկ ապացույց՝ ֆիլմի գրառումը, SRT հատվածը, `srtToVtt`-ի հաշվարկը և `<video>`-ի `<track>`-ը։ Եթե կարողացար նույնը պատմել առանց «թարգմանիչը ամեն վայրկյան միանում է» քայլ ավելացնելու, ամբողջ ճանապարհը վերականգնել ես։

### Որտե՞ղ փոխել ինչ

| Քո հարցը | Սկզբում բացիր | Ինչու հենց այստեղ |
|---|---|---|
| Ուզում եմ փոխել ենթագրի գույնը, տառատեսակը կամ ֆոնը։ | Պատրաստի կայք՝ [catalog-site/catalog.css](catalog-site/catalog.css), `#hosted-player::cue`։ Տեղական դիտում՝ [static/media.css](static/media.css), `video::cue`։ Հավելում՝ [extension/content.js](extension/content.js), `layout` և `attach`։ | Նախ որոշիր՝ ներկառուցված ենթագրի՞ն ես նայում, թե՞ հավելման նկարած տեքստին։ Դրանք առանձին ձևավորում ունեն։ |
| Տողը ճիշտ պահին է սկսվում, բայց ուզում եմ վերև տեղափոխել։ | [catalog-site/player.js](catalog-site/player.js), `subtitles`։ Սեփականատիրոջ կողմից պահելու համար՝ [static/watch.js](static/watch.js), `updateHeightEditor`-ի հարակից պահման կոդը։ | `subtitle_height`-ը էկրանի դիրքն է, իսկ `subtitle_offset`-ը՝ վայրկյանների շեղումը։ |
| Բոլոր տողերը երկու վայրկյան ուշ են, կամ առաջինը շուտ է անհետանում։ | [catalog-site/assets/media-sources.js](catalog-site/assets/media-sources.js), `srtToVtt`։ Սերվերից վերադարձվող VTT-ի դեպքում՝ [app/media_formats.py](app/media_formats.py), `webvtt`։ Հավելման դեպքում՝ [extension/core.js](extension/core.js), `timeline.at`։ | Պարզիր՝ շեղումը գործել է ֆայլի ժամերի՞, թե՞ թվային համեմատության վրա։ |
| Ներբեռնած հայերեն ֆայլում մի տողի վերջը բնագրից տարբեր է։ | [app/subtitles.py](app/subtitles.py), `translated_srt`, հետո՝ `normalize_timings`։ | Տեքստը գտնելուց հետո իրար ծածկող ժամերը կարգավորվում են արտահանման ժամանակ։ |
| Թվում է՝ նույն թարգմանությունը երկու անգամ պահանջվեց։ | [static/file-translator.js](static/file-translator.js), `poll`, ապա [app/translation.py](app/translation.py), `translate`, `cache_key`, `restore_cached`։ | Նախ համեմատիր հարցման հասցեները։ Կրկնվող ընթացքի հարցումը չի թարգմանում։ Gemini կանչի դեպքում համեմատիր `id`-ները, մոդելը, հարակից տեքստը և ձախողված փորձը։ |
| Աշխատանքը վերագործարկումից հետո շարունակվում է տարօրինակ թվից։ | [app/main.py](app/main.py), `get_file_job`, `restore_file_state`, `restore_file_cache`։ Հետո՝ [app/storage.py](app/storage.py), `load_file_job`։ | Այստեղ հանդիպում են պահպանված առաջընթացը, տվյալ ֆայլի մատնահետքը և ստուգված թարգմանությունները։ |
| Բանալին կա, բայց նոր հարցումը սպասում է կամ ասում է, որ սահմանաչափը սպառված է։ | [app/rate_limits.py](app/rate_limits.py), `limits` և `reserve`։ Եթե փոխել ես Google նախագիծը՝ `register_project`։ | Կտեսնես հաշվարկի միջակայքը և որ նախագծի ծախսն է հաշվվում։ |
| YouTube-ում ենթագրեր չեն գտնվել։ | [app/captions.py](app/captions.py), `retrieve_captions` և `english_tracks`։ Հետո՝ [app/main.py](app/main.py), `caption_worker`։ | Կարող ես առանձնացնել՝ աղբյուրը հասանելի՞ էր, համապատասխան լեզու գտնվե՞ց, թե՞ ընթերցումն է ձախողվել։ |
| Ֆիլմը բացվել է, բայց հայերենը չի երևում։ | Պատրաստի կայք՝ [catalog-site/player.js](catalog-site/player.js), `load` և `track`-ի `error` գործողություն։ Տեղական էջ՝ [static/watch.js](static/watch.js), `connect`, `prepareCaptions`։ | `Network`-ում առանձին գտիր տեսանյութի և ենթագրի հարցումները։ Նայիր նաև `track.mode`-ին․ հաջող ստացված տեքստը կարող է անջատված լինել։ |
| Ուզում եմ որոնումը փոխել կամ ֆիլմի քարտի տևողությունը հասկանալ։ | [catalog-site/catalog.js](catalog-site/catalog.js), `render` և `card`։ | Առաջինը զտում է վերնագրերը, երկրորդը հավաքում է քարտը և անհրաժեշտության դեպքում փորձում ստանալ տևողությունը։ |
| Վերսկսելիս ֆիլմը բացվում է սկզբից կամ «նոր» նշանը կորել է։ | [catalog-site/assets/playback-progress.js](catalog-site/assets/playback-progress.js), `read`, `save`, `markOpened`։ | Վերջին 30 վայրկյանում դիրքը մաքրվում է։ Բացելու փաստն ու շարունակելու դիրքը պահվում են առանձին բանալիներով։ |
| Սեփականատերը տեսնում է ֆիլմը, դիտողը՝ ոչ։ | [app/media_api.py](app/media_api.py), `public_videos` և `public_access`։ Պատրաստի կայքի համար՝ [app/catalog_export.py](app/catalog_export.py), `export_library`։ | Տեղական մատչելիությունը, հրապարակման նշումը և կայք արտահանելու համար պիտանի հասցեն տարբեր ստուգումներ են։ |
| Փոխել եմ շապիկը կամ վերնագիրը, կայքում դեռ հինն է։ | [static/poster-editor.js](static/poster-editor.js), `edit`, [app/catalog_sync.py](app/catalog_sync.py), `sync`, ապա՝ [app/catalog_export.py](app/catalog_export.py), `save_manifest`։ | Հետևիր փոփոխությանը՝ սեփականատիրոջ գործողությունից մինչև տեղական ցանկ, ապա ստուգիր տեղադրված տարբերակը։ |
| Վերանվանումից հետո երկու քարտ եմ տեսնում։ | [app/media_api.py](app/media_api.py), `listed_videos` և [tests/test_flat_library.py](tests/test_flat_library.py), `test_renamed_local_file_does_not_leave_a_second_visible_card`։ | Այս տարբերակում վերարտադրվող դեպք է։ Նախ համեմատիր հեռակա աղբյուրի ընտրությունն ու հին տեղական ֆայլի ուղին։ |
| Ուզում եմ հասկանալ՝ այս համակարգից որն է պետք իմ սեփական ծրագրին։ | [catalog-site/watch.html](catalog-site/watch.html)-ի `<video>` և `<track>`, հետո [tests/sample.srt](tests/sample.srt)-ի առաջին հատվածը։ | Ամենափոքր ինքնուրույն նպատակը մեկն է՝ մեկ նախադասություն ցուցադրել նախապես որոշած պահին։ Ցանկը, թարգմանությունն ու պահոցը կարող ես հերթով ավելացնել արդեն աշխատող օրինակին։ |
