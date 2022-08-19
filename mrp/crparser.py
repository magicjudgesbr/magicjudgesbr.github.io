import abc
import codecs
from enum import Enum
from typing import Set

from tika import parser
from pipe import *
import re


class State(Enum):
    INTRO_SECTION = 0
    INDEX_SECTION = 1
    RULES_SECTION = 2
    GLOSSARY_TERM = 3
    GLOSSARY_DEFINITION = 4
    CREDITS_SECTION = 5


class Section(Enum):
    INTRO = 0
    INDEX = 1
    RULES = 2
    GLOSSARY = 3
    CREDITS = 4


class CRWriter(abc.ABC):

    def __init__(self) -> None:
        super().__init__()
        self._contents = ""
        self._sections = {Section.INTRO, Section.INDEX, Section.RULES, Section.GLOSSARY, Section.CREDITS}

    def with_sections(self, sections: Set[Section]):
        self._sections = sections if sections else {Section.INTRO, Section.INDEX, Section.RULES, Section.GLOSSARY, Section.CREDITS}
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def append(self, line: str):
        self._contents += line

    def contents(self):
        return self._contents

    def flush(self, section: Section):
        if self._contents and section in self._sections:
            self._flush_contents(self._contents.strip())
        self._contents = ""

    @abc.abstractmethod
    def _flush_contents(self, contents):
        pass


class CRStdoutWriter(CRWriter):

    def _flush_contents(self, contents):
        print(contents)


class CRFileWriter(CRWriter):

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self._file = None

    def __enter__(self):
        self._file = codecs.open(self.path, "w", "utf-8")
        self._contents = ""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def _flush_contents(self, contents):
        self._file.write(contents + "\n")


class CRPotFileWriter(CRFileWriter):

    def _flush_contents(self, contents):
        self._file.write(f"msgid \"{contents}\"\nmsgstr \"\"\n\n")


class CRStringListWriter(CRWriter):

    def __init__(self) -> None:
        super().__init__()
        self._data = []

    def _flush_contents(self, contents):
        self._data.append(contents)

    def data(self) -> [str]:
        return self._data


class CRParser(object):

    def _process_pdf(self, pdf_file: str, writer: CRWriter, sections: Set[Section] = None) -> None:
        # opening pdf file
        parsed_pdf = parser.from_file(pdf_file)

        data: str = parsed_pdf["content"]
        line: str
        state = State.INTRO_SECTION
        section = Section.INTRO

        with writer.with_sections(sections):

            for line in data.split("\n") | where(lambda x: not x.endswith(".docx")):
                sline = line.strip()

                if state in (State.INTRO_SECTION, State.CREDITS_SECTION):
                    if sline:
                        writer.append(line)
                    else:
                        writer.flush(section)

                    if sline in ("Contents", "Conteúdo") and state == State.INTRO_SECTION:  # start index
                        writer.flush(section)

                        state = State.INDEX_SECTION
                        section = Section.INDEX

                elif state == State.INDEX_SECTION:
                    if sline:
                        writer.append(line)
                        writer.flush(section)

                    if sline in ("Credits", "Créditos"):  # end index
                        state = State.RULES_SECTION
                        section = Section.RULES

                elif state == State.GLOSSARY_TERM:
                    if sline:
                        writer.append(line)
                        writer.flush(section)
                        state = State.GLOSSARY_DEFINITION

                elif state == State.GLOSSARY_DEFINITION:
                    if sline in ("Credits", "Créditos"):
                        writer.flush(section)
                        writer.append(line)
                        writer.flush(section)
                        state = State.CREDITS_SECTION
                        section = Section.CREDITS
                    elif sline:
                        if re.match(r"^\d\.\s", sline) and re.match(r"^\d\.\s", writer.contents()):
                            writer.flush(section)
                        writer.append(line)
                    else:
                        writer.flush(section)
                        state = State.GLOSSARY_TERM

                elif state == State.RULES_SECTION:
                    if re.match(r"^\d+\.(\d[.|\w])?\s[\w\s]+", sline):  # new rule
                        writer.flush(section)
                        writer.append(line)
                    elif sline in ("Glossary", "Glossário"):
                        writer.flush(section)
                        writer.append(line)
                        writer.flush(section)

                        state = State.GLOSSARY_TERM
                        section = Section.GLOSSARY
                    elif sline:
                        writer.append(line)

    def cr_to_txt(self, cr_file, output: str) -> None:
        writer = CRFileWriter(output)
        self._process_pdf(cr_file, writer)

    def cr_to_stdout(self, cr_file) -> None:
        self._process_pdf(cr_file, CRStdoutWriter())

    def cr_to_pot(self, cr_file, output: str) -> None:
        writer = CRPotFileWriter(output)
        self._process_pdf(cr_file, writer)

    def create_translated_po(self, src_pdf, translated_pdf, output):
        src_writer = CRStringListWriter()
        translated_writer = CRStringListWriter()
        self._process_pdf(src_pdf, src_writer)
        self._process_pdf(translated_pdf, translated_writer, {Section.RULES})

        rules_map = {}
        for rule in translated_writer.data():
            matches = re.match(r"^(\d+\.(\s?\d+[.|\w]?)?)", rule)
            if matches:
                rules_map[matches.group(1)] = rule

        with codecs.open(output, "w", "utf-8") as file:
            for src in src_writer.data():
                src = src.replace('"', "”")
                matches = re.match(r"^(\d+\.(\d+[.|\w]?)?)\s", src)
                translated = ""
                if matches:
                    translated = rules_map.get(matches.group(1), "")
                    translated = translated.replace('"', "”")

                file.write(f"msgid \"{src}\"\nmsgstr \"{translated}\"\n\n")
                file.flush()
