import re

class Preper():
    """
    Does preprocessing of text in Farsi (Persian) language
    """

    def __init__(self,text):
        self.text = text

    def remove_noise(self):
        
        self.text = re.sub('[a-zA-Z]', ' ', self.text)
        words = self.text.split()
        return words

    def normalise_letter(self):
        """
        Normalises the text by mapping diffrent glyphs of same letter to one glyph (the most common glyph).
        """
    
        #Normalises letter ا"
        self.text = re.sub('[ﭑآأإٱٲٳٵﭐ]','ا',self.text)
        #Normalising letter "ت"
        self.text = re.sub('[ةٹٺټٽۃ]','ت',self.text)
        #Normalises letter "ک"
        self.text = re.sub('[ػؼكڪګڬڭڮ]','ک',self.text)
        #Normalises letter "گ"
        self.text = re.sub('[ڰڱڲڳڴ]','گ',self.text)
        #Normalises letter "و"
        self.text = re.sub('[ۇؤٶ]','و',self.text)
        #Normalises letter "ه"   
        self.text = re.sub('[ھہەﻫ]','ه',self.text)
        #Normalises letter "ی"
        self.text = re.sub('[ىي]','ی',self.text)
        # Convert Farsi numbers to English numbers
        # Convert Farsi numbers to English numbers
        self.text = re.sub('۰', '0', self.text)
        self.text = re.sub('۱', '1', self.text)
        self.text = re.sub('۲', '2', self.text)
        self.text = re.sub('۳', '3', self.text)
        self.text = re.sub('۴', '4', self.text)
        self.text = re.sub('۵', '5', self.text)
        self.text = re.sub('۶', '6', self.text)
        self.text = re.sub('۷', '7', self.text)
        self.text = re.sub('۸', '8', self.text)
        self.text = re.sub('۹', '9', self.text)
       


        return self.text