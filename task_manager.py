import argparse
import pickle
from datetime import datetime
from pathlib import Path
from operator import attrgetter
from time import strftime

class Task:
    """Representation of a task"""
    def __init__(self,name,due_date,priority=1):
        """If no due date was supplied, assign `None` to due date. Otherwise, format due date and assign
        formatted date to due date"""
        if due_date is not None:
            due_date = datetime.strptime(due_date,'%d/%m/%Y')
            self.due_date = due_date.strftime('%m/%d/%Y')
        else:
            self.due_date = str(due_date)
        self.completed = '-'
        self.created = datetime.now().astimezone()
        self.name = name
        self.unique_id = None
        self.priority = priority
    """Define str method so that the program can print task information/attributes as needed. One of the attributes
    is the age of the task. Accordingly, create an age variable that stores the age of the task by subtracting the 
    time the task was created from the current time and subsequently print the days attribute of the age variable"""
    def __str__(self):
        self.age = datetime.now().astimezone() - self.created
        return str(self.unique_id).ljust(4, ' ') + str(self.age.days) + 'd'.ljust(4,' ') + self.due_date.ljust(15, ' ') + str(self.priority).ljust(10, ' ') + self.name.ljust(22, ' ')

class Tasks:
    """A list of `Task` objects.""" 
    def __init__(self):
        """Read pickled tasks file into a list"""
        # Initialize list of task objects as an empty list
        self.tlist = [] 
        # Try to open previously pickled tasks file if it exists; else, create a pickle file
        # at the provided file path using the Path().touch() function. Once the file is open,  
        # load contents of pickle file into the `self.tlist` list of task objects.
        try:
            with open('.todo.pickle', 'rb') as f:
                self.tlist = pickle.load(f)
        except:
            Path('.todo.pickle').touch()

    def pickle_tasks(self):
        """Pickle task list to a file"""
        with open('.todo.pickle', 'wb') as f:
            pickle.dump(self.tlist, f)

    def add(self,name,due_date,priority=1):
        """Add a new task as a new task object to an existing list of task objects. Notify
        the user about the newly created task"""
        task = Task(name,due_date,priority)
        if self.tlist == []:
            largest_id = 0
        else:
            largest_id = max(t.unique_id for t in self.tlist)
        task.unique_id = largest_id + 1
        self.tlist.append(task)
        print('Created task ' + str(task.unique_id))

    def delete(self, id_to_delete):
        """As long as there is a task to delete, delete the task based on inputted task ID. If no tasks
        exist or the inputted ID does not match the ID of any existing tasks, notify the user"""
        if self.tlist != []:
            for t in self.tlist:
                if t.unique_id == id_to_delete:
                    task_index = self.tlist.index(t)
                    self.tlist.pop(task_index)
                    print("Deleted task " + str(t.unique_id))
                    return
        print('Could not find task to delete')

    def list(self):
        """List all incomplete tasks in descending order according to priority: highest to lowest."""
        headers = 'ID'.ljust(4, ' ') + 'Age'.ljust(5,' ') + 'Due Date'.ljust(15,' ') + 'Priority'.ljust(10, ' ') + 'Task'.ljust(22, ' ') 
        dividers = '--'.ljust(4, ' ') + '---'.ljust(5,' ') + '------------'.ljust(15,' ') + '--------'.ljust(10,' ') + '--------------------'.ljust(22, ' ') 
        print(headers)
        print(dividers)
        self.tlist = sorted(self.tlist,key=attrgetter('priority'),reverse=True)
        for each_task in self.tlist:
            if each_task.completed == '-':
                print(each_task)

    def report(self):
        """List all tasks, regardless of whether they are complete or incomplete. 

        If the task is incomplete, format the created date only and print the task along with the created date. A dash under
        `Completed` denotes that there is no completed date and the task is not yet completed. If the task is complete, list
        the created and completed dates in addition to all of the other attributes.
        
        Sort all tasks by priority, in descending order from highest to lowest."""
        headers = 'ID'.ljust(4, ' ') + 'Age'.ljust(5,' ') + 'Due Date'.ljust(15,' ') + 'Priority'.ljust(10, ' ') + 'Task'.ljust(22, ' ') + 'Created'.ljust(35, ' ') + 'Completed'.ljust(27, ' ')
        dividers = '--'.ljust(4, ' ') + '---'.ljust(5,' ') + '------------'.ljust(15,' ') + '--------'.ljust(10,' ') + '--------------------'.ljust(22, ' ') + '----------------------------'.ljust(35, ' ') + '----------------------------'.ljust(28, ' ')
        print(headers)
        print(dividers)
        self.tlist = sorted(self.tlist,key=attrgetter('priority'),reverse=True)
        for task in self.tlist:
            if task.completed == '-':
                created_date = task.created.strftime("%a %b %#d %X ")  + task.created.tzname()  + task.created.strftime(" %Y")
                print(task, end='')
                print(created_date.ljust(35, ' ') + task.completed.ljust(27,' '))
            else:
                completed_date = task.completed.strftime("%a %b %#d %X ")  + task.completed.tzname()  + task.completed.strftime(" %Y")
                created_date = task.created.strftime("%a %b %#d %X ")  + task.created.tzname()  + task.created.strftime(" %Y")
                print(task, end='')
                print(created_date.ljust(35, ' ') + completed_date.ljust(27,' '))
        

    def done(self, id_to_complete):
        """Loop through list of tasks and check if inputted ID matches the ID of any of the tasks. If it does,
        mark the respective task as complete by overwriting its completed attribute with the current time in 
        the local timezone and notify user regarding completion. If the inputted ID does not match any of the 
        existing ID's, notify user that the application was not able to find a task with the inputted ID"""
        for t in self.tlist:
            if t.unique_id == id_to_complete:
                t.completed = datetime.now().astimezone()
                print("Completed task " + str(t.unique_id))
                return
        print('Could not find task with id ' + str(id_to_complete))

    def query(self, queries):
        """Loop through list of queries and see if any of the queries in the list is a part of a task name and, if so, 
        if that task is incomplete. If both of these two conditions are met, mark the respective query as a match and
        print that task"""
        query_matches = []
        for query in queries:
            for task in self.tlist:
                if query.lower() in task.name.lower() and task.completed == '-':
                    query_matches.append(task)
        headers = 'ID'.ljust(4, ' ') + 'Age'.ljust(5,' ') + 'Due Date'.ljust(15,' ') + 'Priority'.ljust(10, ' ') + 'Task'.ljust(22, ' ') 
        dividers = '--'.ljust(4, ' ') + '---'.ljust(5,' ') + '------------'.ljust(15,' ') + '--------'.ljust(10,' ') + '--------------------'.ljust(22, ' ')
        print(headers)
        print(dividers)
        for match in query_matches:
            print(match)

def main():
    """Create ArgumentParser object and fill object with information regarding program arguments by calling `add_argument`
    method. After doing so, parse the user's supplied arguments and execute arguments. Finally, save the new data to a pickle
    file for future reuse and exit the program"""
    parser = argparse.ArgumentParser(description='Update your To Do List.')

    #Add arguments
    #Add argument, add, that adds a new task
    parser.add_argument('--add', type=str, required=False, help='a task string to add to your list')
    #Add argument, due, that adds the due date for a task
    parser.add_argument('--due', type=str, required=False, help='due date in dd/MM/YYYY format')
    #Add argument, priority, that adds the priority of task as a number between 1 and 3 with 3 being the highest and 1 being the lowest
    parser.add_argument('--priority', type=int, required=False, default=1, help='priority of task; default is 1')
    #Add argument, query, that uses the user's supplied keywords to search the task list for tasks that include these keywords
    parser.add_argument('--query', type=str, required=False, nargs='+', help='search task list by keyword')
    #Add argument, list, that lists all tasks that have not yet been completed
    parser.add_argument('--list', action='store_true', required=False, help='list all tasks that have not been completed')
    #Add argument, delete, that deletes an existing task
    parser.add_argument('--delete', type=int,required=False,help='insert unique id of task to delete')
    #Add argument, report, that reports all tasks, incomplete or complete
    parser.add_argument('--report', action='store_true', required=False, help='provide a report of all tasks, complete or incomplete')
    #Add argument, done, that marks a task complete
    parser.add_argument('--done',type=int,required=False,help='insert unique id of task to complete')

    # Parse arguments
    args = parser.parse_args()
    # Create instance of Tasks
    task_list = Tasks()

    # Execute arguments 
    if args.add:
        task_list.add(args.add, args.due, args.priority)
    elif args.list:
        task_list.list()
    elif args.delete:
        task_list.delete(args.delete)
    elif args.report:
        task_list.report()
    elif args.query:
        task_list.query(args.query)
    elif args.done:
        task_list.done(args.done)
    
    #After executing arguments, pickle the final list of tasks
    task_list.pickle_tasks()

    #After pickling the final list of tasks, successfully exit the program
    exit()

if __name__ == '__main__':
    main()

