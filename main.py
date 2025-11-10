from scraper import OpalScraper

def main():
    username = input("Input Opal Username or email：")
    password = input("Input Opal Password：")

    scraper = OpalScraper(username, password)
    scraper.run()

if __name__ == "__main__":
    main()
