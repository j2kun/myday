from datetime import datetime
import pickle
import re

from bs4 import BeautifulSoup
import requests

base_url = 'https://www2.gwu.edu/~erpapers/myday/{}'
years = list(range(1936, 1963))

link_to_filename = dict()
try:
    with open('metadata.pickle', 'rb') as infile:
        link_to_filename = pickle.load(infile)
except:
    print('failed to open metadata')

cached_links = []
try:
    with open('links.pickle', 'rb') as infile:
        cached_links = pickle.load(infile)
except:
    print('failed to open cached_links')

errors = []
try:
    with open('errors.pickle', 'rb') as infile:
        errors = pickle.load(infile)
except:
    print('failed to open errors')


def get_article_urls():
    if cached_links:
        return cached_links

    article_links = []

    for year in years:
        url = base_url.format(year)
        print('Fetching year {}'.format(year))
        response = requests.get(url)
        if response.status_code != 200:
            print('Failed to fetch {}'.format(url))
            continue

        html = BeautifulSoup(response.content, 'html.parser')
        links = html.find_all('a')
        links = [x.attrs['href'].lstrip('./') for x in links if 'displaydoc' in x.attrs['href']]

        article_links.extend([base_url.format(x) for x in links])

    with open('links.pickle', 'wb') as outfile:
        pickle.dump(article_links, outfile)
    return article_links


def date_to_key(date):
    date = date.strip().capitalize()
    date = re.sub(r'Sept', 'Sep', date)
    date = re.sub(r'Sepember', 'Sep', date)
    date = re.sub(r'Spetember', 'Sep', date)
    date = re.sub(r'4th', '4', date)
    parsed_formats = [
        '%B %d, %Y',
        '%B %d %Y',
        '%B %d,%Y',
        '%B %d,%Y',
        '%B, %d, %Y',
        '%b. %d, %Y',
        '%b %d, %Y',
        '%B, %d %Y',
    ]

    for i, fmt in enumerate(parsed_formats):
        try:
            parsed_datetime = datetime.strptime(date, fmt)
            break
        except Exception as e:
            if i == len(parsed_formats) - 1:
                print('Unable to determine date format')
                print(e)
                raise e

    key = '{:4d}-{:02d}-{:02d}'.format(
        parsed_datetime.year, parsed_datetime.month, parsed_datetime.day
    )
    return key


def get_articles(article_links):
    all_filenames = set(link_to_filename.values())
    for _url in article_links:
        url = _url[:-1] + _url[-1].lower()
        try:
            if url in link_to_filename or url in errors:
                continue

            bad_links = ['md000586', 'md057074b']
            if any(x in url for x in bad_links):
                continue

            response = requests.get(url)
            if response.status_code != 200:
                print('Failed to fetch {}'.format(url))
                continue

            html = BeautifulSoup(response.content, 'html.parser')
            try:
                date = html.find_all('h2', {'class': 'release-date'})[0].text
            except:
                continue
            key = date_to_key(date)
            if 'md055947b' in url:
                key = '1941-07-25'
            elif 'md000222' in url:
                key = '1944-12-30'
            elif 'md001390' in url:
                key = '1949-09-21'

            doc_body = html.find('div', {'class': 'docBody'})
            paragraphs = [x.text for x in doc_body.find_all('p')]
            text = '\n\n'.join(paragraphs)

            filename = '{}.txt'.format(key)
            n = 0
            while filename in all_filenames:
                n += 1
                filename = '{}_{}.txt'.format(key, n)

            print('writing {}'.format(filename))
            with open('data/{}'.format(filename), 'w') as outfile:
                outfile.write(text)
            link_to_filename[url] = filename
            all_filenames.add(filename)
        except (Exception, KeyboardInterrupt) as e:
            print('Failed on {}'.format(url))
            errors.append(url)
            print(e)
            with open('metadata.pickle', 'wb') as outfile:
                pickle.dump(link_to_filename, outfile)
            with open('errors.pickle', 'wb') as outfile:
                pickle.dump(errors, outfile)


if __name__ == "__main__":
    print('Fetching links.')
    links = get_article_urls()
    print('Fetching article texts.')
    articles = get_articles(links)
