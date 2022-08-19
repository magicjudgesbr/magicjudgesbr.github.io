import logging
import shutil
import os
import yaml
import sass
import json
import gettext
import re
from requests import request
from slugify import slugify
from livereload import Server
from jinja2 import Environment, FileSystemLoader, contextfilter

from mrp.structurer import RulesStructurer


def slug_filter(txt, **kwargs):
    return slugify(txt, **kwargs)


def copy_tree(src, dst, ignore=None):
    if not os.path.exists(src):
        return
    for item in os.listdir(src):
        item_src = os.path.join(src, item)
        item_dst = os.path.join(dst, item)
        if os.path.isdir(item_src):
            if os.path.exists(item_dst):
                shutil.rmtree(item_dst)
            shutil.copytree(
                item_src,
                item_dst,
                ignore=shutil.ignore_patterns(*ignore) if ignore is not None else ignore,
            )
        else:
            shutil.copy2(item_src, item_dst)

    if not os.path.isdir(dst):
        return

    # remove empty subfolders
    def remove_empty_folders(path):
        entries = os.listdir(path)
        for entry in entries:
            fullpath = os.path.join(path, entry)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)

        if len(os.listdir(path)) == 0:
            os.rmdir(path)

    remove_empty_folders(dst)


template_env = Environment(
    loader=FileSystemLoader("src/templates"),
    extensions=['jinja2.ext.i18n', 'jinja2.ext.do']
)
translations = gettext.translation(
    domain="comprehensive-rules",
    localedir="data",
    languages=["pt"]
)
template_env.install_gettext_translations(translations)


class TemplateFilters(object):
    allowed_terms = []
    rule_pattern = re.compile(r'((\d{3}(\.\d+\w?)?)(, [“"][\w,.\s]+[”"])?)')
    rule_section_pattern = re.compile(r'((\d), [“"][\s\w.,]+[”"])')
    symbols_pattern = re.compile(r'\{([^{}]+)\}')
    card_img_pattern = re.compile(r'\[\[([^\[\]]+)\]\]')

    def __init__(self, cr, symbols):
        self.terms = []
        for entry in cr["glossary"]:
            if entry["term"].lower() in self.allowed_terms:
                self.terms.append(translations.gettext(entry["term"]).lower())

        self.symbols = symbols

    def ref_rules(self, value):
        id, text = value.split(" ", maxsplit=1)
        text = self._check_rule_ref(text)
        text = self._check_rule_section_ref(text)
        return f"{id} {text}"

    def glossary(self, value):
        for term in self.terms:
            pattern = re.compile(f"\\b{re.escape(term)}s?\\b", re.IGNORECASE)
            match = pattern.search(value)
            if match:
                value = self._wrap_term(value, match, term)

        return value

    def mtg_symbols(self, value):
        matches = self.symbols_pattern.finditer(value)

        for match in reversed([m for m in matches]):
            symbol = match.group(1).replace("/", "")
            if symbol in self.symbols:
                value = self._wrap_symbol(value, match, symbol)
            else:
                print(symbol, value)
        return value

    def mtg_card_image(self, value):
        matches = self.card_img_pattern.finditer(value)

        for match in reversed([m for m in matches]):
            card_name = match.group(1)
            if card_name:
                value = self._wrap_card_img(value, match, card_name)
        return value

    def _wrap_term(self, value, match, term):
        term = slug_filter(term)
        return f"{value[:match.start()]}<span class='tooltip term-{term}'>{value[match.start():match.end()]}</span>{value[match.end():]}"

    def _wrap_symbol(self, value, match, symbol):
        text_symbol = value[match.start():match.end()]
        return f"{value[:match.start()]}<span class='symbol'><img title={text_symbol} src='/symbols/{symbol}.png' alt='{text_symbol}'/><span>{text_symbol}</span></span>{value[match.end():]}"

    def _wrap_card_img(self, value, match, card_name):
        response = request("GET", f"https://api.scryfall.com/cards/named?exact={card_name}")
        if response.ok:
            payload = response.json()
            gatherer = payload["related_uris"]["gatherer"]
            card_img = payload["image_uris"]["normal"]
            return f"{value[:match.start()]}<span class='card-img'><a href='{gatherer}' target='_blank'>{card_name}<span><img src='{card_img}' alt='{card_name}'s image'/></span></a></span>{value[match.end():]}"
        else:
            self.logger.warning(f"Card {card_name} not found!")
        return card_name

    def _wrap_rule_link(self, value, match, link):
        try:
            if value.rindex("<a", 0, match.start()) and value.index('</a>', match.end()):
                return value
        except:
            pass
        return f"{value[:match.start()]}<a href='{link}'>{value[match.start():match.end()]}</a>{value[match.end():]}"

    def _check_rule_ref(self, text):
        matches = self.rule_pattern.finditer(text)

        for match in reversed([m for m in matches]):
            rule = match.group(2)
            if "." in rule:
                subgroup, subrule = rule.split(".")
                group = subgroup[0]
                link = f"/regras/cr/{group}/{subgroup}/#{subrule}"
            else:
                group = rule[0]
                subgroup = rule
                link = f"/regras/cr/{group}/{subgroup}"

            text = self._wrap_rule_link(text, match, link)

        return text

    def _check_rule_section_ref(self, text):
        matches = self.rule_section_pattern.finditer(text)

        for match in reversed([m for m in matches]):
            section = match.group(2)
            link = f"/regras/cr/{section}/"

            text = self._wrap_rule_link(text, match, link)

        return text

    def _check_rule_group_ref(self, text):
        matches = self.rule_group_pattern.finditer(text)

        for match in reversed([m for m in matches]):
            rule = match.group(2)
            group = rule[0]
            subgroup = rule
            link = f"/regras/cr/{group}/{subgroup}"

            text = self._wrap_rule_link(text, match, link)

        return text


def translate_glossary_entry(entry):
    term = entry["term"]
    desc = entry["desc"]
    entries = []
    if term == "Counter":
        entries.append({
            "term": translations.gettext(term),
            "desc": [translations.gettext(desc[0])]
        })
        entries.append({
            "term": "Marcadores",
            "desc": [translations.gettext(desc[1])]
        })
    elif term == "Draw":
        entries.append({
            "term": translations.gettext(term),
            "desc": [translations.gettext(desc[0])]
        })
        entries.append({
            "term": "Empate",
            "desc": [translations.gettext(desc[1])]
        })
    elif term == "Exile":
        entries.append({
            "term": translations.gettext(term),
            "desc": [translations.gettext(desc[0]), translations.gettext(desc[2])]
        })
        entries.append({
            "term": "Exilar",
            "desc": [translations.gettext(desc[1])]
        })
    else:
        entries.append({
            "term": translations.gettext(entry["term"]),
            "desc": map(translations.gettext, desc)
        })
    return entries


class BuildPipeline(object):
    logger = logging.getLogger(__name__)
    src_dir = "src/"
    dst_dir = "docs/"
    simple_pages = ["index", "about"]
    scripts = ["main.js"]
    config = None
    cr = {}
    symbols = set()

    def start(self):
        # first build
        try:
            self.build()
        except Exception as ex:
            self.logger.exception(ex)
            pass
        # watcher
        server = Server()
        server.watch("src/**/*", self.build)
        server.serve(root="docs/")

    def build(self):
        with open(os.path.join(self.src_dir, "config.yml")) as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)

        self.logger.info("building...")
        self._load_symbols()
        self._parse_rules_structure()

        filters = TemplateFilters(self.cr, self.symbols)
        template_env.filters["ref_rules"] = filters.ref_rules
        template_env.filters["glossary"] = filters.glossary
        template_env.filters["mtg_symbols"] = filters.mtg_symbols
        template_env.filters["mtg_card_image"] = filters.mtg_card_image
        template_env.filters["slug"] = slug_filter

        self._copy_assets()
        self._copy_static()
        self._process_sass()

        self._create_terms_classes()

        self._process_templates()
        self._create_search_data()

    def _copy_assets(self):
        assets_dir = os.path.join(self.src_dir, "assets/")
        copy_tree(assets_dir, os.path.join(self.dst_dir, "assets/"), ignore=["*.scss"])

    def _copy_static(self):
        static_dir = os.path.join(self.src_dir, "static/")
        copy_tree(static_dir, self.dst_dir)

    def _process_sass(self):
        css = sass.compile(
            filename=os.path.join(self.src_dir, "assets/scss/main.scss"),
            output_style='compressed'
        )

        output_dir = os.path.join(self.dst_dir, "assets/css")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(os.path.join(output_dir, "main.css"), "w") as file:
            file.write(css)

    def _get_page_output_file(self, page_data, template):
        output_file = os.path.join(self.dst_dir, page_data["url"][1:], template.name)
        if page_data["url"][-1] == "/":
            output_file = os.path.join(self.dst_dir, page_data["url"][1:], "index.html")

        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        return output_file

    def _process_templates(self):
        # create simple pages

        for simple_page in self.simple_pages:
            template = template_env.get_template(f"{simple_page}.html")
            page_data = self.config["site"]["pages"][simple_page]
            output_file = self._get_page_output_file(page_data, template)

            with open(output_file, "w") as out:
                out.write(template.render(page=page_data, **self.config))

        for script in self.scripts:
            template = template_env.get_template(f"{script}")
            output_file = os.path.join(self.dst_dir, "assets/js", template.name)

            with open(output_file, "w") as out:
                out.write(template.render(**self.config))

        self._create_cr_pages()

    def _parse_rules_structure(self):
        # comprehensive rules
        structurer = RulesStructurer()
        self.cr = structurer.process("data/en/comprehensive-rules.txt")
        cr_data = self.config["site"]["pages"]["cr"]
        cr_data["has_children"] = True
        cr_data["children"] = []
        pages = self.config["site"]["pages"]
        for group in self.cr["rules"]:
            rule_group = self.cr["rules"][group]
            group_title = translations.gettext(f"{group}. {rule_group['name']}")
            page_id = f"cr_{group}"
            group_children = []
            pages[page_id] = {
                "title": group_title,
                "url": f"/regras/cr/{group}/",
                "parent": cr_data["title"],
                "has_children": True,
                "children": group_children,
                "template": "rules-group",
                "group": group,
                "content_class": "rules"
            }
            cr_data["children"].append(page_id)

            for item in rule_group["items"]:
                subgroup = item["group"]
                subgroup_title = translations.gettext(f"{subgroup}. {item['name']}")
                page_id = f"cr_{group}_{subgroup}"
                pages[page_id] = {
                    "title": subgroup_title,
                    "url": f"/regras/cr/{group}/{subgroup}/",
                    "parent": group_title,
                    "grand_parent": cr_data["title"],
                    "template": "rules-subgroup",
                    "group": group,
                    "subgroup": subgroup,
                    "content_class": "rules"
                }
                group_children.append(page_id)

        # glossary
        glossary_title = translations.gettext("Glossary")
        page_id = "cr_glossary"
        pages[page_id] = {
            "title": glossary_title,
            "url": "/regras/cr/glossario/",
            "parent": cr_data["title"],
            "template": "glossary",
        }
        cr_data["children"].append(page_id)

    def _create_cr_pages(self):
        template = template_env.get_template("rules-index.html")
        page_data = self.config["site"]["pages"]["cr"]

        output_file = self._get_page_output_file(page_data, template)

        with open(output_file, "w") as out:
            out.write(template.render(page=page_data, **self.config, cr=self.cr))

        for page_id in self.config["site"]["pages"]:
            page_data = self.config["site"]["pages"][page_id]
            if page_id.startswith("cr") and "template" in page_data:
                template = template_env.get_template(f"{page_data['template']}.html")
                output_file = self._get_page_output_file(page_data, template)

                with open(output_file, "w") as out:
                    if page_data["template"] == "glossary":
                        translated_glossary = []
                        for entry in self.cr["glossary"]:
                            translated_entries = translate_glossary_entry(entry)
                            translated_glossary.extend(translated_entries)

                        out.write(template.render(page=page_data, **self.config, glossary=translated_glossary))
                    elif "subgroup" in page_data:
                        items = self.cr["rules"][page_data["group"]]["items"]
                        subgroup = page_data["subgroup"]
                        index = int(subgroup) - int(subgroup[0]) * 100
                        rules = items[index]["rules"]
                        out.write(template.render(page=page_data, **self.config, rules=rules))
                    else:
                        out.write(template.render(page=page_data, **self.config))

    def _create_search_data(self):
        search_data = {}
        for group in self.cr["rules"]:
            rule_group = self.cr["rules"][group]
            items = rule_group["items"]
            group_title = translations.gettext(f"{group}. {rule_group['name']}")
            for item in items:
                subgroup_title = translations.gettext(f"{item['group']}. {item['name']}")
                content = ""

                for rule in item["rules"]:
                    rule_content = translations.gettext(f"{rule['rule']} {rule['text']}")
                    content += "\n" + rule_content
                    rule_title = f"{rule['rule']}"
                    rule_anchor = rule['rule'].split(".", maxsplit=1)[1]
                    if rule_anchor[-1] == ".":
                        rule_anchor = rule_anchor[:-1]

                    search_data[rule['rule']] = {
                        "doc": subgroup_title,
                        "title": rule_title,
                        "content": rule_content.strip(),
                        "url": f"/regras/cr/{group}/{item['group']}/#{rule_anchor}"
                    }

                search_data[item['group']] = {
                    "doc": group_title,
                    "title": subgroup_title,
                    "content": content.strip(),
                    "url": f"/regras/cr/{group}/{item['group']}/"
                }

        for entry in self.cr["glossary"]:
            term = translations.gettext(entry["term"])
            term_link = slug_filter(term)
            content = "\n".join(map(translations.gettext, entry["desc"]))
            search_data[entry["term"]] = {
                "doc": "Glossário",
                "title": term,
                "content": content,
                "url": f"/regras/cr/glossario/#{term_link}"
            }

        with open(os.path.join(self.dst_dir, "assets/js/search-data.json"), "w") as file:
            json.dump(search_data, file)

    def _create_terms_classes(self):
        template = template_env.get_template("terms.css")

        output_file = os.path.join(self.dst_dir, "assets/css/terms.css")

        with open(output_file, "w") as out:
            out.write(template.render(glossary=self.cr["glossary"], **self.config))

    def _load_symbols(self):
        self.symbols = set()
        for file in os.listdir(os.path.join(self.src_dir, "static/symbols")):
            self.symbols.add(os.path.splitext(file)[0])
