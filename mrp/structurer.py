import codecs
from enum import Enum
import re
import datetime


class State(Enum):
    INITIAL = 0
    EFFECTIVE = 1
    INTRO = 2
    TOC = 3


EFFECTIVE_DATE_PATTERN = re.compile("These rules are effective as of (\\w+ \\d+, \\d+)\\.")

class RulesStructurer:

    def process(self, filename):
        with codecs.open(filename, "r", "utf-8") as file:
            lines = file.readlines()
        return self._process_cr(lines)

    def _process_cr(self, lines):
        lc = 0
        cr = {
            "intro": []
        }
        state = State.INITIAL

        for line in lines:
            line = line.strip()
            lc += 1
            if not line:
                continue

            if state == State.INITIAL:
                match = EFFECTIVE_DATE_PATTERN.match(line)
                if match:
                    strdate = match.group(1)
                    date = datetime.datetime.strptime(strdate, "%B %d, %Y")
                    cr["effective_date"] = date
                    cr["effective_date_str"] = line
                    state = State.INTRO
                else:
                    cr["title"] = line

            elif state == State.INTRO:
                if line == "Introduction":
                    continue
                if line == "Contents":
                    state = State.TOC
                cr["intro"].append(line)
            elif state == State.TOC:
                pass

        return cr

