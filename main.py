import logging
from mrp.pipeline import BuildPipeline
from mrp.generator import POGenerator

if __name__ == '__main__':
    POGenerator().generate("data/en/comprehensive-rules.txt", "data/en/comprehensive-rules.pot")
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]: %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    pipeline = BuildPipeline()
    pipeline.start()
