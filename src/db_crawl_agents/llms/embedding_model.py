from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class SBERTModel:
  def __init__(self, model_path: str) -> None:
    """
    Initialize the SBERTModel with the specified model file path.

    Parameters:
      model_path (str): Path to the SBERT model file, which can be a local file or
               an identifier for a model hosted on the Hugging Face Model Hub.

    Raises:
      Exception: If the model fails to load during initialization.
    """
    self.model_path = model_path
    self.model = None
    self.load_model()

  def load_model(self) -> None:
    """
    Load the SBERT model from the specified file path.

    This method initializes the model using the SentenceTransformer library.

    Raises:
      Exception: If there is an error loading the model, logs the error message.
    """
    try:
      self.model = SentenceTransformer(self.model_path)
    except Exception as e:
      logger.warning(f"Error loading the model: {e}")
      raise

  def get_model(self) -> SentenceTransformer:
    """
    Retrieve the loaded SBERT model.

    Returns:
      SentenceTransformer: The loaded SBERT model.

    Raises:
      ValueError: If the model has not been loaded yet, indicating that the
            load_model() method has not been called or has failed.
    """
    if self.model is None:
      raise ValueError("The model has not been loaded. Please call load_model() first.")
    return self.model