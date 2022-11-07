import os
import re

import requests
import pickle
import json

from bs4 import BeautifulSoup, SoupStrainer
from nltk import word_tokenize


def extract_urls(link) -> list:
    r = requests.get(link)
    data = r.text
    soup = BeautifulSoup(data, parseOnlyThese=SoupStrainer("td"), features="html.parser")
    x = soup.findAll("a")

    scraped_urls = []

    for tr in x:
        links = tr.get('href')
        scraped_urls.append("https://catalog.utdallas.edu" + str(links))

    scraped_urls = set(scraped_urls)
    print(len(scraped_urls))
    return scraped_urls


def scrape_text(list_of_urls):
    for url in list_of_urls:
        try:
            r = requests.get(url, timeout=20)
        except requests.exceptions.RequestException as e:
            continue

        soup = BeautifulSoup(r.text, 'html.parser')

        course_prefix = url[url.rfind('/') + 1:]
        course_prefix = course_prefix.upper()
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(directory + "/" + course_prefix + '.txt', 'w', encoding="utf-8") as f:
            text = []
            for data in soup.find_all("p"):
                current_line = data.get_text()
                if len(current_line) > 0:
                    text.append(current_line)

            f.write("\n".join(text))
            f.close()

            print('Year ' + str(year) + ' ' + plan + ' ' + course_prefix)


def fill_course_object():
    if not os.path.exists(directory):
        return
    for index_file, file in enumerate(os.listdir(directory)):
        filename = os.fsdecode(file)
        with open(directory + '/' + filename, 'r', encoding="utf-8") as f:
            text = f.read()
            text = text.split('\n')
            for line in text:
                current_course = Course(line)
                if current_course.course_number not in course_set:
                    course_set.add(current_course.course_number)
                    course_list.append(current_course)
                    current_course.print()
                    data[current_course.course_number] = json.loads(current_course.obj_to_json())
            f.close()


def create_json():
    with open('cs_catalog.json', 'w') as output_JSON:
        json.dump(data, output_JSON, ensure_ascii=False, indent=4, sort_keys=True)
        output_JSON.close()
        print(len(data))


def clean_course_list() -> dict:
    newDict = dict()
    for key in data.keys():
        if key == "":
            continue

        # Include for graduate courses
        #if key[-4] != "6" and key[-4] != "5":
        #    continue

        # Include for CS courses
        if ('CS' in key or 'SE' in key or 'ECS' in key or 'ECSC' in key)\
                and not ('MSEN' in key or 'SYSE' in key or 'HCS' in key or 'EECS' in key
                         or 'SOCS' in key or 'ISEC' in key or 'EPCS' in key):
            newDict[key] = data[key]
    return newDict

def removeStringJunk(curr) -> str:
    curr = curr.replace(' ,', ',')
    curr = curr.replace(' .', '.')
    curr = curr.replace(' :', ':')
    curr = curr.replace(' ;', ';')
    curr = curr.replace(" \'", "\'")
    curr = curr.replace('( ', '(')
    curr = curr.replace(' )', ')')
    curr = curr.replace('[ ', '[')
    curr = curr.replace(' ]', ']')
    curr = curr.replace(' - ', '-')
    return curr


if __name__ == '__main__':
    class Course:
        course_number = ""
        course_title = ""
        course_year = ""
        course_hours = ""
        course_description = ""

        def __init__(self):
            self.course_year = year
            self.course_number = ""

        def __init__(self, line):
            self.course_year = str(year)
            self.parse_course_information(line)

        def parse_course_information(self, line):
            # Course Number
            tokens = word_tokenize(line)
            if len(tokens) < 1:
                return
            self.course_number = tokens[0] + ' ' + tokens[1]
            self.course_number = self.course_number.upper()
            if self.course_number in course_set:
                return

            tokens = tokens[2:]

            # Equivalent Names
            if tokens[0] == '(':
                end_index = tokens.index(')') + 1
                opt_pattern = '([A-Z]{2,4} (([0-9]{4})|([0-9][vV]([0-9]{2}))|([0-9]-{3})){1})'
                self.course_equivalent = self.get_course_nums(tokens[0:end_index], opt_pattern)
                tokens = tokens[end_index:]

            # Course Title
            end_of_title_index = tokens.index('(')
            self.course_title = " ".join(tokens[0:end_of_title_index])
            self.course_title = removeStringJunk(self.course_title)
            self.course_title = self.course_title
            tokens = tokens[end_of_title_index:]

            if tokens[0] == '(':
                end_index = tokens.index(')') + 1
                self.course_hours = " ".join(tokens[1:end_index - 1])
                self.course_hours = self.course_hours.replace("semester", "")
                self.course_hours = self.course_hours.replace("credit", "")
                self.course_hours = self.course_hours.replace("hours", "")
                self.course_hours = self.course_hours.replace("hour", "")
                self.course_hours = self.course_hours.replace(" ", "")
                tokens = tokens[end_index:]

            # Course Prereq
            minIndex = len(tokens)
            if 'Prerequisite' in tokens:
                minIndex = min(tokens.index('Prerequisite'), minIndex)
            if 'Prerequisites' in tokens:
                minIndex = min(tokens.index('Prerequisites'), minIndex)
            if 'Corequisite' in tokens:
                minIndex = min(tokens.index('Corequisite'), minIndex)
            if 'Corequisites' in tokens:
                minIndex = min(tokens.index('Corequisites'), minIndex)
            tokens = tokens[:minIndex]
            self.course_description = " ".join(tokens)
            self.course_description = removeStringJunk(self.course_description)
            self.course_description = re.sub(" \((\d|\[\d-\d\] )-(\d|\[\d-\d\])\) \w", "", self.course_description)

        def get_course_nums(self, tokens: list, pattern: str) -> list:
            opt_token = ' '.join(tokens)
            course_tokens = re.finditer(pattern, opt_token)
            course_tokens = [num[0] for num in course_tokens]
            return course_tokens

        def obj_to_json(self) -> dict:
            dictionary = {
                'Title': self.course_title,
                'Description': self.course_description,
                'Hours': self.course_hours,
                'Year': self.course_year
            }
            temp = json.dumps(dictionary)
            return temp

        def print(self):
            print(self.course_number + ' ' + self.course_title + ' hours:' + self.course_hours)


    course_list = []
    course_set = set()
    data = {}
    for year in range(2022, 2012, -1):
        for plan in ["graduate", "undergraduate"]:
            curr_url = "https://catalog.utdallas.edu/" + str(year) + "/" + plan + "/courses/school"

            if not os.path.exists('pickle_files/' + plan + '/urls_' + str(year) + '.pickle'):
                if not os.path.exists('pickle_files/' + plan):
                    os.makedirs('pickle_files/' + plan)

                urls = extract_urls(curr_url)
                with open('pickle_files/' + plan + '/urls_' + str(year) + '.pickle', 'wb') as handle:
                    pickle.dump(urls, handle)
                    handle.close()
            else:
                with open('pickle_files/' + plan + '/urls_' + str(year) + '.pickle', 'rb') as handle:
                    urls = pickle.load(handle)
                    handle.close()

            directory = 'Courses/' + plan + '/' + str(year)
            if not os.path.exists(directory):
                os.makedirs(directory)
                scrape_text(urls)
            fill_course_object()
    data.pop("", None)
    data = clean_course_list()
    create_json()
