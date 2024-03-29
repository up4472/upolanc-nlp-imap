from source.model.model_base        import Model

from tensorflow.keras.optimizers    import Adam
from tensorflow.keras.losses        import SparseCategoricalCrossentropy
from sklearn.preprocessing          import LabelEncoder
from transformers                   import BertTokenizer
from transformers                   import TFBertForSequenceClassification
from sklearn.model_selection        import train_test_split

import tensorflow
import numpy
import tqdm
import os

class Bert (Model) :

	def __init__ (self, params, classes) :
		super().__init__(params)

		self.n = classes
		self.name = str(params.y).lower().replace(' ', '') + str(self.n)
		self.path = r'resources\\models\\pretrained\\custom\\' + self.name
		self.tokenizer = BertTokenizer.from_pretrained('bert-base-cased')

		if os.path.exists(self.path) :
			self.model = TFBertForSequenceClassification.from_pretrained(self.path)
		else :
			self.model = TFBertForSequenceClassification.from_pretrained(
				r'resources\models\pretrained\english',
				num_labels = self.n,
				from_pt = True
			)

			optimizer = Adam(learning_rate = 1e-5, epsilon = 1e-08, clipnorm = 1.0)
			loss = SparseCategoricalCrossentropy(from_logits = True)

			self.model.compile(loss = loss, optimizer = optimizer, metrics = ['accuracy'])

		self.encoder = LabelEncoder()

	def __convert_to_input (self, data, pad_token = 0, pad_token_segment_id = 0, max_length = 128) :
		input_ids       = []
		attention_masks = []
		token_type_ids  = []

		for x in tqdm.tqdm(data, position = 0, leave = True) :
			inputs = self.tokenizer.encode_plus(x, add_special_tokens = True, max_length = max_length)

			i = inputs['input_ids']
			t = inputs['token_type_ids']
			m = [1] * len(i)

			padding_length = max_length - len(i)

			i = i + ([pad_token] * padding_length)
			m = m + ([0] * padding_length)
			t = t + ([pad_token_segment_id] * padding_length)

			input_ids.append(i)
			attention_masks.append(m)
			token_type_ids.append(t)

		return [
			numpy.asarray(input_ids),
			numpy.asarray(attention_masks),
			numpy.asarray(token_type_ids)
		]

	def __example_to_features (self, input_ids, attention_masks, token_type_ids, y) :
		return {
			'input_ids'         : input_ids,
			'attention_mask'    : attention_masks,
			'token_type_ids'    : token_type_ids
		}, y

	def encode (self, y) :
		return self.encoder.fit_transform(y.to_numpy().astype(str)).astype(float)

	def fit (self, x, y, epochs = 2, validation_percent = 0.15, allow_import = True) :
		if os.path.exists(self.path) and allow_import :
			self.model = TFBertForSequenceClassification.from_pretrained(self.path)
		else :
			y = self.encoder.fit_transform(y.to_numpy().astype(str)).astype(float)
			x0, x1, y0, y1 = train_test_split(x, y, test_size = validation_percent, random_state = 0)

			x0 = self.__convert_to_input(x0.astype(str))
			x1 = self.__convert_to_input(x1.astype(str))

			ds0 = tensorflow.data.Dataset.from_tensor_slices(
				(
					x0[0],
					x0[1],
					x0[2],
					y0
				)
			).map(self.__example_to_features).shuffle(100).batch(12).repeat(5)

			ds1 = tensorflow.data.Dataset.from_tensor_slices(
				(
					x1[0],
					x1[1],
					x1[2],
					y1
				)
			).map(self.__example_to_features).batch(12)

			self.model.fit(ds0, epochs = epochs, validation_data = ds1, verbose = 0)

			if self.params.should_save :
				os.mkdir(self.path)

				self.model.save_pretrained(self.path)

		return self

	def predict (self, x) :
		n = len(x)

		x = self.__convert_to_input(x.astype(str))
		s = tensorflow.data.Dataset.from_tensor_slices(
			(
				x[0],
				x[1],
				x[2],
				numpy.ones(n)
			)
		).map(self.__example_to_features).batch(12)

		self.model = self.model.from_pretrained(self.path)

		return numpy.argmax(self.model.predict(s).logits, axis = 1)
