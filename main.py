import time
import urllib3
from multiprocessing import Process, Pipe, Array
import curses


# TODO:
# - Implement database
# - Implement focus search
# - Implement preknowledge

class Crawler():
    def __init__(self, site, parent=None, depth=0):
        self.title = site
        self.parent = parent
        self.depth = depth + 1

    def print(self):
        print(self.title, " ->")
        if self.parent == None: return print()
        self.parent.print()


def complete(targetSite, links, parent, conn, manager):
    if not targetSite in links: return False

    print()
    manager.print_final()
    child = Crawler(targetSite, parent, parent.depth)
    print("FOUND!", f'Depth: {child.depth}')
    child.print()
    conn.send("Done")
    return True


def crawl(stack, targetSite, id, conn, manager=None):
    maxChecks = 250

    checked = []
    visits = 0

    # Iterate
    while stack:
        startTime = time.time()
        parent = stack.pop(0)
        visits += 1

        # Get HTML content from link
        page = openLink(parent.title)
        if not page: continue

        # Get bread text
        contentStart = 'id="bodyContent'
        contentEnd = 'id="References"'
        content = page.split(contentStart)[1]
        contentEndIndex = content.find(contentEnd)
        content = content[:contentEndIndex]

        # Get links
        links = content.split('<a href="/wiki/')
        links.remove(links[0])  # Remove first part

        # Separate link
        links = [
            title[:title.find('"')]
            for title in links
        ]

        if complete(targetSite, links, parent, conn, manager): return True

        for title in links:
            if title in checked: continue
            child = Crawler(title, parent, parent.depth)
            stack.append(child)
            checked.append(title)

        # Print status of processors
        if manager:
            manager.update_values(id, parent.depth, stack, visits, checked, startTime)
            manager.print_process()

        if id == 0: return stack
        if visits > maxChecks: break


class Manager:
    def __init__(self, conn):
        self.conn = conn
        self.depth = Array('i', processorAmount)
        self.stack = Array('i', processorAmount)
        self.visits = Array('i', processorAmount)
        self.checks = Array('i', processorAmount)
        self.time = Array('i', processorAmount)
        self.startTime = time.time()

    def update_values(self, id, depth, stack, visits, checked, startTime):
        self.depth[id - 1] = depth
        self.stack[id - 1] = len(stack)
        self.visits[id - 1] = visits
        self.checks[id - 1] = len(checked)
        timeTaken = time.time() - startTime
        self.time[id - 1] = round(timeTaken * 1000)

    def print_final(self):
        print(f'Processors:')
        print(f'Depth    = {self.depth[:]})')
        print(f'Stack    = {self.stack[:]})')
        # print(f'sum({sum(self.checks[:])})')
        print(f'Visits   = {self.visits[:]})')
        print(f'Checked  = {self.checks[:]}')
        print(f'Millisec = {self.time[:]})')
        print()

    def print_process(self):
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()

        stdscr.addstr(0, 0, "Processors:")
        stdscr.addstr(1, 0, f"Depth    = {self.depth[:]}")
        stdscr.addstr(2, 0, f"Stack    = {self.stack[:]} ({sum(self.stack[:])})")
        stdscr.addstr(3, 0, f"Visits   = {self.visits[:]} ({sum(self.visits[:])})")
        stdscr.addstr(4, 0, f"Checked  = {self.checks[:]} ({sum(self.checks[:])})")
        stdscr.addstr(5, 0, f"Millisec = {self.time[:]}")
        totalTime = time.time() - self.startTime
        stdscr.addstr(6, 0, f"Time (s) = {totalTime}")
        stdscr.addstr(7, 0, f"")
        stdscr.refresh()


def runProcessors(stack, child_conn):
    processors = []
    manager = Manager(child_conn)
    chunkSize = int(len(stack) / processorAmount)

    for i in range(processorAmount):
        chunk = stack[:chunkSize]
        stack = stack[chunkSize:]
        processor = Process(target=crawl, args=(chunk, targetSite, i + 1, child_conn, manager))
        processors.append(processor)

    for processor in processors: processor.start()

    if parent_conn.recv() == "Done":
        for processor in processors: processor.terminate()


def openLink(title):
    address = 'https://en.wikipedia.org/wiki/'
    link = address + title
    http = urllib3.PoolManager()
    request = http.request('GET', link)
    page = request.data.decode('utf-8')
    notFoundMessage = "Wikipedia does not have an article with this exact name"
    if notFoundMessage in page: return None
    return page


def init(startSite, targetSite):
    startSite = startSite.replace(" ", "_")
    targetSite = targetSite.replace(" ", "_")
    if openLink(startSite) == None: raise ValueError("{startSite} not in Wikipedia")
    if openLink(targetSite) == None: raise ValueError("{targetSite} not in Wikipedia")

    return startSite, targetSite


if __name__ == "__main__":
    startSite = "Europe"
    startSite = "Smirnoff"
    targetSite = "Nursing home"
    # targetSite = "Speech–language pathology"
    # targetSite = "Boiling"
    processorAmount = 5

    # -------------------------

    timeStart = time.time()

    # print('\u001b[4m\u001b[1m')
    print(f'Start: {startSite} -> Target: {targetSite}')
    # print('\u001b[0m')

    startSite, targetSite = init(startSite, targetSite)

    parent_conn, child_conn = Pipe()
    stack = crawl([Crawler(startSite)], targetSite, 0, child_conn)
    runProcessors(stack, child_conn)

    timeTaken = time.time() - timeStart
    print(f'Time taken: {timeTaken}')