import logging
import shutil
import os
import yaml
import sass
import gettext
from livereload import Server
from jinja2 import Environment, FileSystemLoader

from mrp.structurer import RulesStructurer

template_env = Environment(
    loader=FileSystemLoader("src/templates"),
    extensions=['jinja2.ext.i18n']
)
template_env.install_gettext_translations(gettext.translation(
    domain="comprehensive-rules",
    localedir="data",
    languages=["pt"]
))


def copy_tree(src, dst, ignore=None):
    if not os.path.exists(src):
        return
    for item in os.listdir(src):
        item_src = os.path.join(src, item)
        item_dst = os.path.join(dst, item)
        if os.path.isdir(item_src):
            shutil.copytree(item_src, item_dst, ignore=shutil.ignore_patterns(*ignore), dirs_exist_ok=True)
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


class BuildPipeline(object):
    logger = logging.getLogger(__name__)
    src_dir = "src/"
    dst_dir = "docs/"
    simple_pages = ["index", "about"]
    scripts = ["main"]
    config = None
    cr = {}

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
        self._copy_assets()
        self._copy_static()
        self._process_sass()
        self._parse_rules_structure()
        self._process_templates()

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
            template = template_env.get_template(f"{script}.js")
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
            group_title = gettext.gettext(f"{group}. {rule_group['name']}")
            page_id = f"cr_{group}"
            group_children = []
            pages[page_id] = {
                "title": group_title,
                "url": f"/regras/cr/{group}/",
                "parent": cr_data["title"],
                "has_children": True,
                "children": group_children
            }
            cr_data["children"].append(page_id)

            for item in rule_group["items"]:
                subgroup = item["group"]
                subgroup_title = gettext.gettext(f"{subgroup}. {item['name']}")
                page_id = f"cr_{group}_{subgroup}"
                pages[page_id] = {
                    "title": subgroup_title,
                    "url": f"/regras/cr/{group}/{subgroup}",
                    "parent": group_title,
                }
                group_children.append(page_id)

    def _create_cr_pages(self):
        template = template_env.get_template("rules-index.html")
        page_data = self.config["site"]["pages"]["cr"]

        output_file = self._get_page_output_file(page_data, template)

        with open(output_file, "w") as out:
            out.write(template.render(page=page_data, **self.config, cr=self.cr))
