import codecs
from enum import Enum
import re
import datetime
import logging


class State(Enum):
    INITIAL = 0
    EFFECTIVE = 1
    INTRO = 2
    TOC = 3
    DISCARD = 4
    RULES_GROUP = 5
    RULES_SUBGROUP = 6
    GLOSSARY = 7
    CREDITS = 8
    FOOTNOTE = 9


EFFECTIVE_DATE_PATTERN = re.compile("These rules are effective as of (\\w+ \\d+, \\d+)\\.")


class RulesStructurer:
    logger = logging.getLogger(__name__)

    def process(self, filename):
        with codecs.open(filename, "r", "utf-8") as file:
            lines = file.readlines()
        return self._process_cr(lines)

    def _process_cr(self, lines):
        lc = 0
        cr = {
            "intro": [],
            "rules": {},
            "glossary": [],
            "credits": [],
        }
        state = State.INITIAL
        current_rules_group = None
        current_rules_subgroup = None
        current_term = None
        current_is_blank = False

        for line in lines:
            line = line.strip()
            lc += 1
            last_was_blank = current_is_blank
            if not line:
                current_is_blank = True
                continue
            current_is_blank = False
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
                    continue
                cr["intro"].append(line)
            elif state == State.TOC:
                if line == "Glossary":
                    state = State.DISCARD
                    continue
                group, name = line.split(".", maxsplit=1)
                if len(group) == 1:
                    cr["rules"][group] = {
                        "group": group,
                        "name": name.strip(),
                        "items": []
                    }
                else:
                    parent_group = group[0]
                    cr["rules"][parent_group]["items"].append({
                        "group": group,
                        "name": name.strip(),
                        "parent": parent_group,
                        "rules": []
                    })
            elif state == State.DISCARD:
                if "." not in line:
                    continue
                group, name = line.split(".")
                if group in cr["rules"] and not current_rules_group:
                    current_rules_group = cr["rules"][group]
                    state = State.RULES_GROUP
                    continue
                self.logger.warn(f"Discarding {line}...")

            elif state == State.RULES_GROUP:
                group, name = line.split(".")
                if not current_rules_group:
                    self.logger.error(f"Wrong state for line {lc}: {line}")
                    break
                index = int(group) - int(group[0]) * 100
                current_rules_subgroup = current_rules_group["items"][index]
                state = State.RULES_SUBGROUP

            elif state == State.RULES_SUBGROUP:
                if line == "Glossary":
                    state = State.GLOSSARY
                    continue
                if line.startswith("Example:"):
                    current_rules_subgroup["rules"][-1]["examples"].append(line)
                    continue

                number, text = line.split(" ", maxsplit=1)
                if number.endswith("."):
                    group = number[:-1]
                    if "." not in number[:-1]:
                        # changed subgroup
                        if int(group) < 100:
                            # changed group
                            current_rules_group = cr["rules"][group]
                            current_rules_subgroup = None
                            continue
                        index = int(group) - int(group[0]) * 100
                        current_rules_subgroup = current_rules_group["items"][index]

                current_rule = {
                    "rule": number,
                    "text": text.strip(),
                    "group": group.split(".", maxsplit=1)[0],
                    "examples": []
                }
                current_rules_subgroup["rules"].append(current_rule)

            elif state == State.GLOSSARY:
                if line == "Credits":
                    state = State.CREDITS
                    continue
                if current_term is None or last_was_blank:
                    current_term = {
                        "term": line,
                        "desc": []
                    }
                    cr["glossary"].append(current_term)
                else:
                    current_term["desc"].append(line)
            elif state == State.CREDITS:
                match = EFFECTIVE_DATE_PATTERN.match(line)
                if match:
                    state = State.FOOTNOTE
                    continue
                cr["credits"].append(line)
            elif state == State.FOOTNOTE:
                cr["footnote"] = line

        return cr
