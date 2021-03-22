import pandas

#
# Public methods
#

def loadtxt (path, encode = 'utf8') :
	with open(path, 'r', encoding = encode) as file :
		text = file.read()

	return text

def loadxlsx (path, sheet = None) :
	return pandas.read_excel(path, sheet_name = sheet)
