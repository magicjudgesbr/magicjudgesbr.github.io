import logging
from mrp.pipeline import BuildPipeline
from mrp.generator import POGenerator

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]: %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    import os
    logging.info(os.getcwd())
    pipeline = BuildPipeline()
    pipeline.build()
