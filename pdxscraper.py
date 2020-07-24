from bs4 import BeautifulSoup
import csv
import mechanize
import random
import time
import argparse

class Scraper:
  BASE_URL = 'http://dpsstnet.state.or.us/PublicInquiry_CJ/SMSGoPerson.aspx'
  DEPARTMENT_NAME = 'Portland Police Bureau'

  def __init__(self, max_sleep=5):
    self.browser = mechanize.Browser()
    self.current_response = None
    self.rows = []
    self.file = None
    self.csv = None
    self.max_sleep = max_sleep

  def start_search(self, pattern='*'):
    # Open the page
    self.browser.open(self.BASE_URL)
    # Grab the form
    self.browser.select_form('FormLogin')
    form = self.browser.forms()[0]
    # Fill in whatever we plan to search for
    form.find_control('txtFindValue').value = pattern
    # Submit it
    self.current_response = self.browser.submit('Button1')
    # And process the results
    self.file = open('output.tsv', 'w')
    self.csv = csv.writer(self.file, delimiter="\t")

    self.write_row(['name', 'department', 'id', 'id2', 'status', 'rank'])
    self.process_page()
    self.file.close()

  def process_page(self):
    # read in the response
    data = self.current_response.read()
    soup = BeautifulSoup(data, 'html.parser')
    # Get the table we want
    table = soup.find(id='DataGridAgcyEmp')
    # Get the rows. First one has headings, last is navigation, so we skip those
    self.rows = table.find_all('tr')[1:-1]
    self.process_rows()
    self.go_to_next_page()

  def process_rows(self):
    for row in self.rows:
      # links
      a_name, a_dept = row.find_all('a')
      # Make sure this is one we want
      if a_dept.text.strip != self.DEPARTMENT_NAME:
        next

      link = a_name['href']
      name = a_name.text.strip()
      self.get_record(link)
      

  def get_record(self, link):
    id = link.split('=')[-1]
    page = self.browser.open('http://dpsstnet.state.or.us/PublicInquiry_CJ/' + link)
    soup = BeautifulSoup(page.read(), 'html.parser')
    name = soup.find(id='txtEmpName').text.strip()
    empInfo2 = soup.find(id='txtEmpInfo2').text.strip()
    status = soup.find(id='txtEmpStat').text.strip()
    rank = soup.find(id='txtEmpRank').text.strip()

    self.write_row([name, self.DEPARTMENT_NAME, id, empInfo2, status, rank])

    self.browser.back()

  def go_to_next_page(self):
    try:
      self.browser.find_link('Next')
      self.browser.select_form('FormAgcyEmp')
      field = self.browser.form.find_control('__EVENTTARGET')
      field.readonly = False
      # the javascript swaps the '$' for ':'
      field.value = 'DataGridAgcyEmp:_ctl54:_ctl1'
      # disable submit buttons. if these are enabled self.browser.submit() uses
      # them instead, which resets the search.
      for c in self.browser.form.controls:
        if c.type == 'submit':
          c.disabled = True
      # sleep between requests when self.max_sleep > 0
      time.sleep(random.randint(0, self.max_sleep))
      self.current_response = self.browser.submit()
      self.process_page()
    except mechanize._mechanize.LinkNotFoundError as error:
      pass

  def write_row(self, columns):
    self.csv.writerow(columns)

if __name__=='__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('query', type=str, help='Search query to issue')
  parser.add_argument('-s', '--max-sleep', type=int, default=5, help='Upper limit on random sleep time in seconds between requests (use 0 for no sleep)')
  args = parser.parse_args()
  print('args: ', args)
  if args.max_sleep < 0:
    raise argparse.ArgumentTypeError('max_sleep value must be >= 0, saw %d' % args.max_sleep)
  scrapper = Scraper(max_sleep=args.max_sleep)
  scrapper.start_search(args.query)
