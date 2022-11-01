import os
import re

import requests
import pickle

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

            print('Year ' + str(year) + ' ' + course_prefix)


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
            f.close()


def create_json():
    with open('course_catalog.json', 'w') as f:
        f.write('{\n')
        for index, current_course in enumerate(course_list):
            f.write('\t\"' + current_course.course_number + '\": {\n')
            f.write('\t\t\"Title\": ' + '\"' + current_course.course_title + '\",\n')
            f.write('\t\t\"Year\": ' + '\"' + current_course.course_year + '\",\n')
            f.write('\t\t\"Equivalent\": ')
            if not len(current_course.course_equivalent) > 0:
                f.write('"",\n')
            else:
                f.write("\"")
                for i, c in enumerate(current_course.course_equivalent):
                    f.write(c)
                    if i+1 != len(current_course.course_equivalent):
                        f.write(" | ")
                f.write("\",\n")
            f.write('\t\t\"Prerequisite\": ')
            if not len(current_course.course_pre) > 0:
                f.write('""\n')
            else:
                f.write("\"" + current_course.course_pre + "\"\n")
            if index != len(course_list)-1:
                f.write('\t},\n')
            else:
                f.write('\t}\n')
        f.write('}')
        f.close()


def clean_course_list(list_of_courses) -> list:
    new_list = []
    for course in list_of_courses:
        if len(course.course_number) < 5:
            continue
        if course.course_number[-4] == '6' or course.course_number[-4] == '5':
            new_list.append(course)
    return new_list


if __name__ == '__main__':
    class Course:
        course_number = ""
        course_title = ""
        course_year = ""
        course_equivalent = []
        course_pre = []

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
            self.course_title.replace(' , ', ', ')
            tokens = tokens[end_of_title_index:]

            # Course Prereq
            if 'Prerequisite' in tokens or 'Prerequisites' in tokens:
                if not re.search('([A-Z]{2,4} (([0-9]{4})|([0-9][vV]([0-9]{2}))|([0-9]-{3})))', " ".join(tokens)):
                    return
                pre_pattern = '([A-Z]{2,4} (([0-9]{4})|([0-9][vV]([0-9]{2}))|([0-9]-{3})){1})|or|and|either|,|\(|\)'
                if 'Prerequisite' in tokens:
                    end_of_pre_index = tokens.index('Prerequisite')
                else:
                    end_of_pre_index = tokens.index('Prerequisites')
                tokens = tokens[end_of_pre_index + 2:len(tokens) - 4]
                res = ''
                for m in re.finditer(pre_pattern, " ".join(tokens)):
                    res += m.group() + ' '
                res.replace('|', 'or')
                res.replace('&', 'and')

                self.course_pre = res

        def get_course_nums(self, tokens: list, pattern: str) -> list:
            opt_token = ' '.join(tokens)
            course_tokens = re.finditer(pattern, opt_token)
            course_tokens = [num[0] for num in course_tokens]
            return course_tokens

        def print(self):
            print(self.course_number + ' ' + self.course_title, end=' ')
            if len(self.course_equivalent) > 0:
                print(self.course_equivalent)
            if len(self.course_pre) > 0:
                print(self.course_pre)


    course_list = []
    course_set = set()
    for year in range(2022, 2012, -1):
        curr_url = "https://catalog.utdallas.edu/" + str(year) + "/graduate/courses/school"

        if not os.path.exists('pickle_files/urls_' + str(year)):
            os.makedirs('pickle_files/urls_' + str(year))

            urls = extract_urls(curr_url)
            with open('pickle_files/urls_' + str(year) + '.pickle', 'wb') as handle:
                pickle.dump(urls, handle)
                handle.close()
        else:
            with open('pickle_files/urls_' + str(year) + '.pickle', 'rb') as handle:
                urls = pickle.load(handle)
                handle.close()

        directory = 'Courses/' + str(year)
        if not os.path.exists(directory):
            os.makedirs(directory)
            scrape_text(urls)
        fill_course_object()
    course_list = clean_course_list(course_list)
    create_json()
