from abc import ABC, abstractmethod

class BaseResolver(ABC):

    @abstractmethod
    def resolve(self, data):
        pass
