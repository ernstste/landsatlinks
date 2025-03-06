import os
import unittest
from pathlib import Path

from landsatlinks.utils import load_secret


class TestUtils(unittest.TestCase):

    def create_tmp_dir(self):
        """
        Create a temporary directory for the calling test method.
        """
        root = Path(__file__).parents[1] / 'tmp'
        path = root / self.__class__.__name__ / self._testMethodName
        os.makedirs(path, exist_ok=True)
        return path

    def test_load_secret(self):
        result1 = ['app-token', 'user', 'token']
        result2 = ['user', 'password']
        valid_examples = [
            (result1, 'app-token\nuser\ntoken'),
            (result1, 'app-token\n\tuser\t\ntoken\n\n'),
            (result1, '\napp-token\nuser\ntoken  '),
            (result2, 'user\npassword'),
            (result2, 'user\npassword\n\n'),
            (result2, '\nuser\npassword\t\n'),
        ]

        tmp_dir = self.create_tmp_dir()

        for i, (expected, example) in enumerate(valid_examples):
            path = tmp_dir / f'secret_example_{i}.txt'
            with open(path, 'w') as f:
                f.write(example)
            result = load_secret(path.as_posix())
            self.assertEqual(result, expected, f'Example {i + 1}:"{example}"\nexpected {expected}, got {result}')


if __name__ == '__main__':
    unittest.main()
