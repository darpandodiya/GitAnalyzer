import csv
import datetime
import sqlalchemy
import os

'''
This script takes input data from CSV files, parses and adds into PostgreSQL instance. 

The data is added in relational format for Usecase 1, 2 and 3. 

SQLAlchemy package is used to interact with database. 

TODO: Refactor code, especially seperate static strings into their own class file.
'''

# CSV parsing
from sqlalchemy import create_engine, MetaData, Table, select

# POSTGRES = {
#     'user': 'postgres',
#     'pw': 'pg123',
#     'db': 'demo2',
#     'host': 'localhost',
#     'port': '5432',
# }

# POSTGRES = {
#     'user': 'bpvmzwecssmefd',
#     'pw': '3de40800289f2251c3192849dcfc0fec4216bc90b080f60a8d77efd37156b278',
#     'db': 'd7ehdb25kv3pkv',
#     'host': 'ec2-184-73-210-189.compute-1.amazonaws.com',
#     'port': '5432',
# }

def storeAll(uc1df,uc2df,uc3df,structure):

    engine = create_engine(os.environ['DATABASE_URL'], echo=False)
    metadata = MetaData(engine)
    engine.connect()

    # Define tables
    repos_table = Table('Repos', metadata, autoload=True)
    authors_table = Table('Authors', metadata, autoload=True)
    files_table = Table('Files', metadata, autoload=True)
    subexperts_table = Table('SubjectExperts', metadata, autoload=True)
    filedependencies_table = Table('FileDependencies', metadata, autoload=True)
    bugprobabilities_table = Table('BugProbabilities', metadata, autoload=True)
    structure_table = Table('RepoStructures', metadata, autoload = True)
    conn = engine.connect()

    # Use case 1

    print("Starting data insertion of use case 1")

    for _,row in uc1df.iterrows():
        RepoName = row['RepoName']
        RepoUrl = row['RepoUrl']
        FilePath = row['FilePath']
        LastModified = row['LastModified']
        FileSizeBytes = row['FileSizeBytes']
        LinesOfCode = row['LinesOfCode']
        AuthorName = row['AuthorName']
        AuthorEmail = row['AuthorEmail']
        Score = float(row['Score'])

        FileName = FilePath.split("/")[-1]
        FileType = FilePath.split(".")[-1].upper()

        # Check if the repo is already existing in the database
        select_repo = select([repos_table]).\
            where((repos_table.c.RepoName == RepoName) & (repos_table.c.RepoUrl == RepoUrl))

        result = conn.execute(select_repo)
        row = result.fetchone()
        # print(str(select_repo))

        # A record already exists
        if result.rowcount > 0:
            print("Repo already exists. With RepoId: " + str(row['RepoId']))
            repoId = row['RepoId']

        # Otherwise, insert new record
        else:
            insert_repos = repos_table.insert().values(
                RepoName=RepoName,
                RepoUrl=RepoUrl,
            )
            result = conn.execute(insert_repos)
            repoId = result.inserted_primary_key[0]
            print("Inserted new repo with RepoId: " + str(repoId))

        # Check if author already present or not
        select_authors = select([authors_table]). \
            where((authors_table.c.AuthorName == AuthorName) & (authors_table.c.AuthorEmail == AuthorEmail))

        result = conn.execute(select_authors)
        row = result.fetchone()
        # print(str(select_repo))

        # A record already exists
        if result.rowcount > 0:
            print("Author already exists. With AuthorId: " + str(row['AuthorId']))
            authorId = row['AuthorId']

        # Insert new author otherwise
        else:
            insert_authors = authors_table.insert().values(
                AuthorName=AuthorName,
                AuthorEmail=AuthorEmail,
            )
            result = conn.execute(insert_authors)
            authorId = result.inserted_primary_key[0]
            print("Inserted new author with ID: " + str(authorId))

        # Check if file already present or not
        select_dest_file = select([files_table]). \
            where((files_table.c.RepoId == repoId) & (files_table.c.FilePath == FilePath))

        result = conn.execute(select_dest_file)
        row = result.fetchone()

        # A file already exists
        if result.rowcount > 0:
            print("File already exists. With FileId: " + str(row['FileId']))
            fileId = row['FileId']
        # Insert new file otherwise
        else:
            insert_files = files_table.insert().values(
                RepoId=repoId,
                FileName=FileName,
                FilePath=FilePath,
                FileType=FileType,
                LastModified=LastModified,
                FileSizeBytes=FileSizeBytes,
                LinesOfCode=LinesOfCode
            )
            result = conn.execute(insert_files)
            fileId = result.inserted_primary_key[0]
            print("New file inserted with fileId : " + str(fileId))

        # Check if this subject expert already exists
        select_subexpert = select([subexperts_table]). \
            where((subexperts_table.c.FileId == fileId) & (subexperts_table.c.AuthorId == authorId))

        result = conn.execute(select_subexpert)
        row = result.fetchone()

        # Author relation already exists
        if result.rowcount > 0:
            print("Author relation already exists. Skipping. (FileId, AuthorId): (" + str(fileId) + "," + str(authorId) + ")")
            continue
        else:
            insert_subexperts = subexperts_table.insert().values(
                FileId=fileId,
                AuthorId=authorId,
                Score=Score
            )
            result = conn.execute(insert_subexperts)
            print("Record inserted with FileId: " + str(fileId) + " AuthorId: " + str(authorId) + " Score: " + str(Score))


    print("-----Use case 1 done.-----")


    # Use case 2

    print("Starting insertion of use case 2")

    for _,row in uc2df.iterrows():
        RepoName = row['RepoName']
        RepoUrl = row['RepoUrl']
        SourceFilePath = row['SourceFilePath']
        DestinationFilePath = row['DestinationFilePath']
        NoOfTimeChanged = row['NoOfTimeChanged']
        NormalizedChanged = float(row['NormalizedChange'])

        # Check if both source and destination files exist. If they do, get their ID
        # Check for repo first
        select_repo = select([repos_table]). \
            where((repos_table.c.RepoName == RepoName) & (repos_table.c.RepoUrl == RepoUrl))

        result = conn.execute(select_repo)
        row = result.fetchone()

        # A record already exists
        if result.rowcount > 0:
            print("Repo already exists. With RepoId: " + str(row['RepoId']))
            repoId = row['RepoId']
        else:
            print("Repo doesn't exist. Skipping this record.")
            continue

        # Check for source file
        select_source_file = select([files_table]). \
            where((files_table.c.RepoId == repoId) & (files_table.c.FilePath == SourceFilePath))

        result = conn.execute(select_source_file)
        row = result.fetchone()

        # Source file already exists
        if result.rowcount > 0:
            print("File already exists. With FileId: " + str(row['FileId']))
            sourceFileId = row['FileId']
        else:
            print("Source file doesn't exist. Skipping this record.")
            continue

        # Check for dest file
        select_dest_file = select([files_table]). \
            where((files_table.c.RepoId == repoId) & (files_table.c.FilePath == DestinationFilePath))

        result = conn.execute(select_dest_file)
        row = result.fetchone()

        # Dest file already exists
        if result.rowcount > 0:
            print("File already exists. With FileId: " + str(row['FileId']))
            destinationFileId = row['FileId']
        else:
            print("Destination file doesn't exist. Skipping this record.")
            continue

        print("Repo, source file and dest file records found. Now inserting into FileDependencies")

        # Check if this file dependency already exists
        select_dependency = select([filedependencies_table]). \
            where((filedependencies_table.c.SourceFileId == sourceFileId) &
                (filedependencies_table.c.DestinationFileId == destinationFileId))

        result = conn.execute(select_dependency)
        row = result.fetchone()

        # Relation already exists
        if result.rowcount > 0:
            print(
                "Relation already exists. Skipping. (SourceFileId, destinationFileId): "
                "(" + str(sourceFileId) + "," + str(destinationFileId) + ")")

        else:
            insert_dependency = filedependencies_table.insert().values(
                SourceFileId=sourceFileId,
                DestinationFileId=destinationFileId,
                NoOfTimeChanged=NoOfTimeChanged,
                NormalizedChanged=NormalizedChanged
            )
            result = conn.execute(insert_dependency)
            print("Record inserted with SourceFileId: " + str(sourceFileId) +
                " DestinationFileId: " + str(destinationFileId) + " NormalizedChanged: " + str(NormalizedChanged))


    print("-----Use case 2 done.-----")


    # Use case 3

    print("Starting insertion of use case 3")
    # csvfile = open('uc3v2.csv', 'r', encoding="utf8")
    # reader = csv.DictReader(csvfile)

    for _,row in uc3df.iterrows():
        RepoName = row['RepoName']
        RepoUrl = row['RepoUrl']
        SourceFilePath = row['SourceFilePath']
        NoOfTimeChanged = row['NoOfTimeChanged']
        BuggyCommits = row['BuggyCommits']
        BuggyCommitsPercentage = float(row['BuggyCommitsPercentage'])

        # Check for repo first
        select_repo = select([repos_table]). \
            where((repos_table.c.RepoName == RepoName) & (repos_table.c.RepoUrl == RepoUrl))

        result = conn.execute(select_repo)
        row = result.fetchone()

        # A record already exists
        if result.rowcount > 0:
            print("Repo already exists. With RepoId: " + str(row['RepoId']))
            repoId = row['RepoId']
        else:
            print("Repo doesn't exist. Skipping this record.")
            continue

        # Check for source file
        select_source_file = select([files_table]). \
            where((files_table.c.RepoId == repoId) & (files_table.c.FilePath == SourceFilePath))

        result = conn.execute(select_source_file)
        row = result.fetchone()

        # Source file already exists
        if result.rowcount > 0:
            print("File already exists. With FileId: " + str(row['FileId']))
            sourceFileId = row['FileId']
        else:
            print("Source file doesn't exist. Skipping this record.")
            continue

        print("Repo, source file records found. Now inserting into BugProbabilities")

        # Check if this relation already exists
        select_dependency = select([bugprobabilities_table]). \
            where((bugprobabilities_table.c.FileId == sourceFileId))
        result = conn.execute(select_dependency)
        row = result.fetchone()

        # Relation already exists
        if result.rowcount > 0:
            print(
                "Relation already exists. Skipping. sourceFileId: " + str(sourceFileId))

        else:
            insert_bugprob = bugprobabilities_table.insert().values(
                FileId=sourceFileId,
                NoOfTimeChanged=NoOfTimeChanged,
                BuggyCommits=BuggyCommits,
                BuggyCommitsPercentage=BuggyCommitsPercentage
            )
            result = conn.execute(insert_bugprob)
            print("Record inserted with fileId: " + str(sourceFileId))


    print("-----Use case 3 done.-----")

    # Store File Structure

    print("Starting insertion of file structure")
    # csvfile = open('uc3v2.csv', 'r', encoding="utf8")
    # reader = csv.DictReader(csvfile)

    RepoName = structure[0]
    RepoUrl = structure[1]
    RepoTree = structure[2]
    # Check for repo first
    select_repo = select([repos_table]). \
        where((repos_table.c.RepoName == RepoName) & (repos_table.c.RepoUrl == RepoUrl))

    result = conn.execute(select_repo)
    row = result.fetchone()

    # A record already exists
    if result.rowcount > 0:
        print("Repo already exists. With RepoId: " + str(row['RepoId']))
        repoId = row['RepoId']
    else:
        print("Repo doesn't exist. Skipping this record.")
        return False

    print("RepoId records found. Now inserting into RepoStructures")

    # Check if this relation already exists
    select_dependency = select([structure_table]). \
        where((structure_table.c.RepoId == repoId))
    result = conn.execute(select_dependency)
    row = result.fetchone()

    # Relation already exists
    if result.rowcount > 0:
        print(
            "Relation already exists. Skipping. RepoId: " + str(repoId))
        
        return repoId

    else:
        insert_bugprob = structure_table.insert().values(
            RepoId=repoId,
            RepoName = RepoName,
            RepoUrl = RepoUrl,
            RepoTree = RepoTree
        )
        result = conn.execute(insert_bugprob)
        print("Record inserted with repoId: " + str(repoId))


    print("-----Structure saving done.-----")

    return repoId