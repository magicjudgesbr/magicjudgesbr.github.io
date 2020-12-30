import logging
from mrp.pipeline import BuildPipeline

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]: %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    pipeline = BuildPipeline()
    pipeline.build()
