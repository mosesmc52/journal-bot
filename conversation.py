class Conversation(object):

    def __init__(self, history_file = './converstion.txt'):
        self.history_file = history_file

    def add_content(self, speaker ,text ):
        with open(self.history_file, "a+") as myfile:
            myfile.write('{}:{}\n'.format(speaker, text))

    def get_entire_history(self):
        with open(self.history_file,mode='r+') as myfile:
            all_of_it = myfile.read()
        return all_of_it
