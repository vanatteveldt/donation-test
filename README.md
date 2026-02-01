# donation-test

Playwright script for automatically testing donations

Usage: (replace the XXXXX in the url by the actual task id from the participant url

```{sh}
pip install -r requirements.txt
playwright install firefox
python test_donation.py YT_small_test_file.zip https://next.eyra.co/a/XXXXXX?p=test_play
```
