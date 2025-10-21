name: Format M3U Files

on:
  push:
    paths:
      - 'input/mysource/*.m3u'
  workflow_dispatch:

jobs:
  format:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Run M3U formatter
        run: |
          python scripts/format_m3u.py

      - name: Commit formatted output
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add output/total.csv output/total.m3u
          git commit -m "Auto update total.csv and total.m3u" || echo "No changes to commit"
          git push
