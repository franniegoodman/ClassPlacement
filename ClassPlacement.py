import csv
import random
from ortools.sat.python import cp_model

def clean_list(s):
    if not s:
        return []
    return [name.strip() for name in s.split(',') if name.strip()]

class Student:
    def __init__(self, name, LG, div, gender, faculty, alum, teacher, sep, tog, notes): 
        self.name = name
        self.LG = LG
        self.div = div
        self.gender = gender
        self.fac = faculty
        self.alum = alum
        self.teacher = teacher
        self.sep = sep if sep is not None else []
        self.tog = tog if tog is not None else []
        self.notes = notes

def makeClasses(filename, outputfile, numteachers):
    file = open(filename)
    reader = csv.reader(file)
    next(reader)
    students = []
    for row in reader:
        # create student object
        student = Student(
            row[0].strip(),  # name
            row[1].strip(),  # LG
            row[2].strip(),  # div
            row[3].strip(),  # gender
            row[4].strip(),  # faculty
            row[5].strip(),  # alum
            row[8].strip(),  # teacher
            clean_list(row[9]),  # sep
            clean_list(row[10]),  # tog
            row[7].strip()   # notes
        )
        students.append(student)
        #update totals

    numstudents = len(students)

    model = cp_model.CpModel()
    x = {}

    #boolean for each assignment
    for i in range(numstudents):
        for n in range(numteachers):
            x[(i, n)] = model.NewBoolVar(f'x[{i}, {n}]')

    #hard constraint - each student only assigned to one class
    for i in range(numstudents):
        model.Add(sum(x[(i, n)] for n in range(numteachers)) == 1)

    #initialize penalties and weights for soft constraints
    penalties = {}
    penalties['classSize'] = model.NewIntVar(0, numstudents, 'classSizePen')
    penalties['LG-H'] = model.NewIntVar(0, numstudents, 'LGHPen')
    penalties['LG-M'] = model.NewIntVar(0, numstudents, 'LGMPen')
    penalties['LG-L'] = model.NewIntVar(0, numstudents, 'LGLPen')
    penalties['diversity'] = model.NewIntVar(0, numstudents, 'divPen')
    penalties['gender'] = model.NewIntVar(0, numstudents, 'genderPen')
    penalties['alum'] = model.NewIntVar(0, numstudents, 'alumPen')
    penalties['faculty'] = model.NewIntVar(0, numstudents, 'facPen')

    weights = {
        'classSize': 50,
        'LG-H': 20,
        'LG-M': 20,
        'LG-L': 20,
        'diversity': 20,
        'gender': 20,
        'alum': 5,
        'faculty': 5
    }

    #handle soft constraints
    idealClassSize = numstudents//numteachers
    for n in range(numteachers):
        classSize = sum(x[(i, n)] for i in range(numstudents))
        model.Add(penalties['classSize'] >= classSize - idealClassSize)
        model.Add(penalties['classSize'] >= idealClassSize - classSize)

    idealDivCount = sum(1 for s in students if s.div == 'Y')//numteachers
    for n in range(numteachers):
        divCount = sum(x[(i, n)] for i in range(numstudents) if students[i].div == 'Y')
        model.Add(penalties['diversity'] >= divCount - idealDivCount)
        model.Add(penalties['diversity'] >= idealDivCount - divCount)

    idealGirlCount = sum(1 for s in students if s.gender == 'G')//numteachers
    for n in range(numteachers):
        girlCount = sum(x[(i, n)] for i in range(numstudents) if students[i].gender == 'G')
        model.Add(penalties['gender'] >= girlCount - idealGirlCount)
        model.Add(penalties['gender'] >= idealGirlCount - girlCount)

    idealFacCount = sum(1 for s in students if s.fac == 'Y')//numteachers
    for n in range(numteachers):
        facCount = sum(x[(i, n)] for i in range(numstudents) if students[i].fac == 'Y')
        model.Add(penalties['faculty'] >= facCount - idealFacCount)
        model.Add(penalties['faculty'] >= idealFacCount - facCount)

    idealAlumCount = sum(1 for s in students if s.alum == 'Y')//numteachers
    for n in range(numteachers):
        alumCount = sum(x[(i, n)] for i in range(numstudents) if students[i].alum == 'Y')
        model.Add(penalties['alum'] >= alumCount - idealAlumCount)
        model.Add(penalties['alum'] >= idealAlumCount - alumCount)

    idealHCount = sum(1 for s in students if s.LG == 'H')//numteachers
    idealMCount = sum(1 for s in students if s.LG == 'M')//numteachers
    idealLcount = sum(1 for s in students if s.LG == 'L')//numteachers
    for n in range(numteachers):
        Hcount = sum(x[(i, n)] for i in range(numstudents) if students[i].LG == 'H')
        Mcount = sum(x[(i, n)] for i in range(numstudents) if students[i].LG == 'M')
        Lcount = sum(x[(i, n)] for i in range(numstudents) if students[i].LG == 'L')
        model.Add(penalties['LG-H'] >= Hcount - idealHCount)
        model.Add(penalties['LG-H'] >= idealHCount - Hcount)
        model.Add(penalties['LG-M'] >= Mcount - idealMCount)
        model.Add(penalties['LG-M'] >= idealMCount - Mcount)
        model.Add(penalties['LG-L'] >= Lcount - idealLcount)
        model.Add(penalties['LG-L'] >= idealLcount - Lcount)

    #handle together/separate hard constraints
    def findIndex(name, student_list):
        for index, student in enumerate(student_list):
            if student.name.strip().lower() == name.strip().lower():
                return index
        return None

    for student in students:
        for t in student.tog:
            i = findIndex(student.name, students)
            j = findIndex(t, students)
            if i is not None and j is not None:
                for n in range(numteachers):
                    model.Add(x[(i, n)] == x[(j, n)])
        for s in student.sep:
            i = findIndex(student.name, students)
            j = findIndex(s, students)
            if i is not None and j is not None:
                for n in range(numteachers):
                    model.Add(x[(i, n)] + x[(j, n)] <= 1)

    #minimize penalties
    model.Minimize(sum(weights[p]*penalties[p] for p in penalties))

    #solution class
    class SolutionPrinter(cp_model.CpSolverSolutionCallback):
        def __init__(self, x, students, numteachers, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._x = x
            self._students = students
            self._numteachers = numteachers
            self._solutionCount = 0
            self._solutionLimit = limit
            self.solutions = []
        def on_solution_callback(self):
            self._solutionCount += 1
            solution = []
            for i in range(len(self._students)):
                for n in range(self._numteachers):
                    if self.Value(self._x[(i, n)]):
                        solution.append((self._students[i], n))
            self.solutions.append((self.ObjectiveValue(), solution))
            if self._solutionCount >= self._solutionLimit:
                self.StopSearch()
        def solutionCount(self):
            return self._solutionCount
        
    #solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120.0
    solution_printer = SolutionPrinter(x, students, numteachers, 100000)
    status = solver.Solve(model, solution_printer)
    top5 = sorted(solution_printer.solutions)[:5]

    output = open(outputfile, mode='w')
    writer = csv.writer(output)
    writer.writerow(['Top 5 solutions:'])
    #output
    for i, (val, solution) in enumerate(top5, 1):
        sol = (f"Solution Number: {i}")
        value = (f"Error Value: {val}")
        writer.writerow([sol, value])
        classLists = {}
        for student, num in solution:
            if num+1 not in classLists:
                classLists[num+1] = []
            classLists[num+1].append(student)
        for n in classLists:
            writer.writerow([n, [s.name for s in classLists[n]]])
            numStudents = len(classLists[n])
            divSum = sum(1 for s in classLists[n] if s.div == 'Y')
            boySum = sum(1 for s in classLists[n] if s.gender == 'B')
            girlSum = sum(1 for s in classLists[n] if s.gender == 'G')
            LGsumL = sum(1 for s in classLists[n] if s.LG == 'L')
            LGsumM = sum(1 for s in classLists[n] if s.LG == 'M')
            LGsumH = sum(1 for s in classLists[n] if s.LG == 'H')
            alumSum = sum(1 for s in classLists[n] if s.alum == 'Y')
            facSum = sum(1 for s in classLists[n] if s.fac == 'Y')
            Notes = {}
            for s in classLists[n]:
                if s.notes != "":
                    Notes[s.name] = s.notes
            writer.writerow([None, f"Total Students: {numStudents}, Diversity Count: {divSum}"])
            writer.writerow([None, f"Boys: {boySum}, Girls:{girlSum}"])
            writer.writerow([None, f"Learning Groups: {LGsumL} L, {LGsumM} M, {LGsumH} H"])
            writer.writerow([None, f"Alumni children: {alumSum}, Faculty Children: {facSum}"])
            writer.writerow([None, f"Notes: {Notes}"])
    output.close()


