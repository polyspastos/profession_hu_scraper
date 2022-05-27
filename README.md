### What is this?
\
A webcrawler for job ads on profession.hu. Basis for the code: [work of mollac](https://github.com/mollac/profession.hu)
<br>
<br>

### How does it work?  
<br>

```
python -m pip install .
python scraper.py
```
or
```
poetry install
poetry run python profession_hu_scraper/scraper.py --pages-to-check 25 --save-to-xlsx True --keyword "cloud fejlesztő"
```

parameter help with adding
```
--help
```
