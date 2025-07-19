# Install
## Python
1. Go to [Python Download](https://www.python.org/downloads)
2. Download Python 3.13.x and install
## Python packages
- For crawling in stealth mode
```
pip install playwright
python -m playwright install
```
- YAML configuration
```
pip install pyyaml
```
# Run
```
e.g.
python .\crawl.py dwmoters
```

# TroubleShooting
## Website Connection Timeout
- e.g. ERR_CONNECTION_TIMED_OUT
- Check your internet connection.
- Check the URL with your browser.
- Use another IP or VPN as crawling may be blocked. 
## Parameters Loading Error
- Error 
```
(venv) PS C:\Dale\Projects\Crawlift\crawler> python .\crawl.py dwmoters
Error: loading parameters from file: expected str, bytes or os.PathLike object, not NoneType
No parameters given.
```
- Check typos in the crawling key. e.g. dwmoters -> dwmotors
