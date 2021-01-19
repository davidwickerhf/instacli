from functools import wraps
import json, click
import os
from os import mkdir
from instacli import BASE_DIR


class Settings():

    SETTINGS_DIR = f'{BASE_DIR}/instacli.json'

    def __init__(self) -> 'Settings':
        """Class that reppresents an abstraction of the settings
        of the `instacli` package.

        Tries to load settings from a `instacli.json` file. If no such
        file is present or if the loaded data is none, a new instace of
        the object will be created and saved in the `instacli.json` file.

        Returns:
            :class:`Setting`: Settings object instance.
        """
        
        try:
            with open(self.SETTINGS_DIR, 'r') as file:
                try:
                    data = json.load(file)
                except:
                    data = None
        except FileNotFoundError:
            data = None

        if not data:
            # Cretate New Setting:
            self.driver_path = None
            self.driver_visible = False
            self.logging = False
            self.output_path = None
            # Save
            des = self._to_dict()
            with open(self.SETTINGS_DIR, 'w') as file:
                json.dump(des, file)
        else:
            # Load existing Setting
            self.driver_path = data.get('driver_path')
            self.driver_visible = data.get('driver_visible')
            self.logging = data.get('logging')
            self.output_path = data.get('output_path')


    def _persistence(func):
        """Function wrapper that saves the changes made to
        the attributes of the `Settings` class into a settings.json file.
        """
        @wraps(func)
        def wrapper(self:'Settings', *args, **kwargs):
            result = func(self, *args, **kwargs)
            # Save
            
            des = self._to_dict()
            with open(self.SETTINGS_DIR, 'w') as file:
                json.dump(des, file)

            return result
        return wrapper


    def _to_dict(self):
        return vars(self)


    @_persistence
    def set_driver_path(self, path:str) -> bool:
        """Validates the inputted path and sets it as
        package setting.

        Args:
            path (str): Path of the chromedriver.exe

        Returns:
            bool: True if path is valid. 
                False if pathis invalid. 
        """
        path = os.path.abspath(path)
        self.driver_path = path

    
    @_persistence
    def set_output_path(self, path:str) -> bool:
        """Validates the inputted path and sets it as
        package setting.

        Args:
            path (str): Path of the output folder

        Returns:
            bool: True if path is valid. 
                False if pathis invalid. 
        """
        path = os.path.abspath(path)
        self.output_path = path
         

    @_persistence
    def set_driver_visible(self, visible:bool):
        self.driver_visible = visible


    @_persistence
    def set_logging(self, logging:bool):
        self.logging = logging