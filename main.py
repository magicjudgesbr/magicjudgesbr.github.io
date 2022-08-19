import logging

from mrp.generator import POGenerator
from mrp.crparser import CRParser

if __name__ == '__main__':

    parser = CRParser()
    # parser.cr_to_txt("data/pdf/en/cr.pdf", "data/pdf/en/cr.txt")
    # parser.cr_to_txt("data/pdf/pt/cr.pdf", "data/pdf/pt/cr.txt")
    # parser.cr_to_stdout("data/pdf/en/cr.pdf")
    # parser.cr_to_stdout("data/pdf/pt/cr.pdf")
    # exit(1)
    # parser.cr_to_txt("data/pdf/en/cr.pdf", "data/en/comprehensive-rules.txt")
    # parser.cr_to_pot("data/pdf/en/cr.pdf", "data/en/LC_MESSAGES/comprehensive-rules.po")
    # parser.create_translated_po("data/pdf/en/cr.pdf", "data/pdf/pt/cr.pdf", "data/pt/LC_MESSAGES/comprehensive-rules.po")

    # POGenerator().generate("data/en/comprehensive-rules.txt", "data/en/comprehensive-rules.pot")
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]: %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    from mrp.pipeline import BuildPipeline
    pipeline = BuildPipeline()
    pipeline.start()
