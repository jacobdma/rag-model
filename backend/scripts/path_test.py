import os

path = r'\\\\EngrNAS\\app_Libraries\\Inventor\\Templates\\2022-Dev\\2019Standard.pdf'
double_path = r'\\EngrNAS\app_Libraries\Inventor\Templates\2022-Dev\2019Standard.pdf'
def test_path():
    print(path)
    norm_path = os.path.normpath(path)
    print(norm_path)
    print(double_path)
    norm_double_path = os.path.normpath(double_path)
    print(norm_double_path)

if __name__ == "__main__":
    test_path()