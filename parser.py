from typing import Dict, List, Union, Any

class Parser():
    def __init__(self):
        pass

    @staticmethod
    def validate_element(data_type: str, element: str) -> Union[str, List[str]]:
            """
            Validate and process the provided 'element' based on the specified 'data_type'.

            Args:
                data_type (str): The type of data processing to be applied. Accepted values:
                                 - 'string': Convert the element to a string.
                                 - 'list': Split the element into a list of words.
                                 - 'list[n:m]': Slice the element into a list from index 'n' to 'm'.
                element (str): The element to be validated and processed.

            Returns:
                Union[str, List[str]]: The processed element based on the data_type.
                                       - If data_type is 'string', returns the element as a string.
                                       - If data_type is 'list', returns a list of words from the element.
                                       - If data_type is 'list[n:m]', returns a list sliced from index 'n' to 'm'.
                                       - If data_type is invalid, raises a ValueError.

            Raises:
                ValueError: If an invalid data_type is specified.
            """

            if 'list[' in data_type:
                temp = data_type.split('[')
                data_type = temp[0]
                try:
                    slice_start = int(temp[1][0])
                except:
                    slice_start = 0
                try:
                    slice_end = int(temp[1][-2])
                except:
                    slice_end = -1
            if data_type == "string":
                return str(element)
            elif data_type == "list":
                return str(element).split()[slice_start:slice_end]
            elif 'list' and '[' in data_type:
                return str(element.split('[')[0]).split()
            else:
                logger.error("Invalid data type specified")
                raise ValueError("Invalid data type specified")

    @staticmethod
    def dict_with_lists_to_list_of_dicts(data: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Parse the scraped data to generate a list of dictionaries.

        Args:
            scraped_data (Dict[str, List[Any]]): A dictionary containing the scraped data.
                                                The keys represent the data names,
                                                and the values are lists of scraped data.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains data from a single entry.
                                  The keys in the dictionary represent the data names,
                                  and the values represent the corresponding scraped data.

        Example:
            If 'scraped_data' is {'name': ['Alice', 'Bob'], 'age': [30, 25]},
            the function will return [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}].
        """
        result = []
        for key, values in data.items():
            for i, element in enumerate(values):
                if i < len(result):
                    result[i].update({key: element})
                else:
                    result.append({key: element})

        return result
