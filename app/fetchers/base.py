from abc import ABC, abstractmethod

class BaseFetcher(ABC):

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def execute(self):
        pass
