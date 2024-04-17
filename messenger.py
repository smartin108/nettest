"""

A simple email sender class

formerly cls_quickmail.py
2021 12 27 - a couple year's old class, refactored (and hopefully improved)

"""

import smtplib

class Quickmail:

    def __init__(self, **kwargs):

        self.gmail_user = 'smartin108@gmail.com'
        self.gmail_password = 'pcqtqrkhzmkfnmff' # generated 2022 04 10
        # set this here: https://myaccount.google.com/apppasswords

        self.subject = kwargs.get('subject')
        self.to = kwargs.get('to')
        self.body = kwargs.get('body')
        self.no_send = kwargs.get('no_send')
        self.sent_from = self.gmail_user  

        if not self.no_send:
            self.send()


    def send(self):
        try:  
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(self.gmail_user, self.gmail_password)
            server.sendmail(self.sent_from, self.to, self.body)
            server.close()
        except Exception as e:
            print(e)
            raise

