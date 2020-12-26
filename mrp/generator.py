import codecs

class POGenerator(object):

    def generate(self, input_file, output_file):
        with codecs.open(input_file, "r", "utf-8") as file:
            lines = file.readlines()

        with codecs.open(output_file, "w", "utf-8") as file:
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                file.write(f"msgid \"{line}\"\nmsgstr \"\"\n\n")
                file.flush()
