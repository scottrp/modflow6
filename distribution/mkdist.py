"""
Python code to create a MODFLOW 6 distribution.  This has been used mostly
on Windows and requires that Latex be installed, and Python with the
pymake package.

To make a distribution:
  1.  Create a release branch
  2.  Update version.txt with the correct minor and micro numbers
  3.  Run the pre-commit.py script, which will create the proper dist name
  4.  Run this mkdist.py script
  5.  Post the distribution zip file
  6.  Commit the release changes, but no need to push
  7.  Merge the release changes into the master branch
  8.  Tag the master branch with the correct version
  9.  Merge master into develop

"""


import os
import sys
import shutil
import subprocess
import zipfile
import pymake
from pymake.download import download_and_unzip
from contextlib import contextmanager

# examples_setup contains code for copying examples into distribution
import examples_setup


@contextmanager
def cwd(path):
    oldpwd=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


def get_distribution_info(versiontexname):
    vername = None
    verdate = None
    fname = versiontexname
    with open(fname) as f:
        lines = f.readlines()
        f.close()
    for line in lines:
        # \newcommand{\modflowversion}{mf6beta0.9.00}
        srchtxt = 'modflowversion'
        if srchtxt in line:
            istart = line.rfind('{') + 1
            istop = line.rfind('}')
            if 0 < istart < istop:
                vername = line[istart: istop]
        srchtxt = 'modflowdate'
        if srchtxt in line:
            istart = line.rfind('{') + 1
            istop = line.rfind('}')
            if 0 < istart < istop:
                verdate = line[istart: istop]
        if verdate is not None:
            break
    return vername, verdate


def zipdir(dirname, zipname):
    print('Zipping directory: {}'.format(dirname))
    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(dirname):
        for file in files:
            if '.DS_Store' not in file:
                fname = os.path.join(root, file)
                print('  Adding to zip: ==> ', fname)
                zipf.write(fname, arcname=fname)
    zipf.close()
    print('\n')
    return


def setup(name, destpath, version, subdirs):
    """
    Setup the folder structure, and return a dictionary of subfolder name
    and the full path in destpath.

    """
    print(2 * '\n')
    print('Setting up {} distribution: {}'.format(name, version))
    print('\n')

    dest = os.path.join(destpath, version)
    if os.path.exists(dest):
        # Raise Exception('Destination path exists.  Kill it first.')
        print('Clobbering destination directory: {}'.format(dest))
        print('\n')
        shutil.rmtree(dest)
    os.mkdir(dest)

    print('Creating subdirectories')
    folderdict = {}
    for sd in subdirs:
        fullpath = os.path.join(dest, sd)
        print('  creating ==> {}'.format(fullpath))
        os.mkdir(fullpath)
        folderdict[sd] = fullpath
    print('\n')

    return folderdict


def copytree(src, dst, symlinks=False, ignore=None):
    """
    Copy a folder from src to dst.  If dst does not exist, then create it.

    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            print('  copying {} ===> {}'.format(s, d))
            shutil.copytree(s, d, symlinks, ignore)
        else:
            print('  copying {} ===> {}'.format(s, d))
            shutil.copy2(s, d)
    return


def convert_line_endings(folder, windows=True):
    """
    Convert all of the line endings to windows or unix

    """
    # Prior to zipping, enforce os line endings on all text files
    print('Converting line endings...')
    platform = sys.platform
    cmd = None
    if platform.lower() == 'darwin':
        if windows:
            cmd = "find . -name '*' | xargs unix2dos"
        else:
            cmd = "find . -name '*' | xargs dos2unix"
    else:
        if windows:
            cmd = 'for /R %G in (*) do unix2dos "%G"'
        else:
            cmd = 'for /R %G in (*) do dos2unix "%G"'
    p = subprocess.Popen(cmd, cwd=folder, shell=True)
    print(p.communicate())
    print('\n')
    return


def change_version_module(fname, version):
    """
    Update the version.f90 source code with the updated version number
    and turn develop mode off.

    """
    with open(fname) as f:
        lines = f.readlines()
    newlines = []
    found1 = False
    found2 = False
    for line in lines:
        newline = line
        srchtxt = 'character(len=40), parameter :: VERSION'
        if srchtxt in line:
            newline = "{} = '{}'".format(srchtxt, version)
            found1 = True
        srchtxt = 'integer(I4B), parameter :: IDEVELOPMODE'
        if srchtxt in line:
            newline = '{} = {}'.format(srchtxt, 0)
            found2 = True
        newlines.append(newline)
    if not found1 or not found2:
        raise Exception('could not replace version or developmode in source code')
    with open(fname, 'w') as f:
        for line in newlines:
            f.write(line.strip() + '\n')
    return


def make_zonebudget(srcpath, destpath, win_target_os, exepath):
    """
    Add zone budget to the distribution

    srcpath should be '../utils/zonebudget'
    destpath should be 'utils'
    sourcepath


    """

    # setup the folder structure
    name = 'zonebudget'
    version = 'zonebudget'
    subdirs = ['src', 'make', 'msvs']
    fd = setup(name, destpath, version, subdirs)

    # copy source folder
    sourcepath = os.path.join(srcpath, 'src')
    copytree(sourcepath, fd['src'], ignore=shutil.ignore_patterns('.DS_Store'))

    # Create makefile in the utils/zonebudget/pymake folder
    print('Creating zonebudget makefile')
    with cwd(os.path.join(srcpath, 'pymake')):
        pymake.main(os.path.join('..', 'src'), 'zbud6', 'gfortran', 'gcc',
                    makeclean=True, dryrun=True, include_subdirs=True,
                    makefile=True, extrafiles='extrafiles.txt')
        os.path.isfile('makefile')

    # Copy makefile to utils/zonebudget/make folder
    shutil.copyfile(os.path.join(srcpath, 'pymake', 'makefile'),
                    os.path.join(srcpath, 'make', 'makefile'))

    # Copy makefile to distribution/xxx/utils/zonebudget/make folder
    shutil.copyfile(os.path.join(srcpath, 'pymake', 'makefile'),
                    os.path.join(fd['make'], 'makefile'))

    # Remove the makefile from the pymake folder
    os.remove(os.path.join(srcpath, 'pymake', 'makefile'))

    # Copy the Visual Studio project file
    flist = [os.path.join(srcpath, 'msvs', 'zonebudget.vfproj')]
    print('Copying zonebudget msvs files')
    for d in flist:
        print('  {} ===> {}'.format(d, fd['msvs']))
        shutil.copy(d, fd['msvs'])
    print('\n')

    # build the executable
    exename = 'zbud6'
    target = os.path.join(exepath, exename)
    if win_target_os:
        fc = 'ifort'
        cc = 'cl'
        exename += '.exe'
    else:
        fc = 'gfortran'
        cc = 'gcc'
    extrafiles = os.path.join(srcpath, 'pymake', 'extrafiles.txt')
    pymake.main(fd['src'], target, fc, cc, makeclean=True,
                include_subdirs=True, extrafiles=extrafiles)
    if win_target_os:
        target += '.exe'
    if not os.path.isfile(target):
        raise Exception('Did not build target: {}'.format(target))

    return


def make_mf5to6(srcpath, destpath, win_target_os, exepath):
    """
    Add mf5to6 to the distribution

    srcpath should be '../utils/mf5to6'
    destpath should be 'utils'
    sourcepath


    """

    # setup the folder structure
    name = 'mf5to6'
    version = 'mf5to6'
    subdirs = ['src', 'make', 'msvs']
    fd = setup(name, destpath, version, subdirs)

    # copy source folder
    sourcepath = os.path.join(srcpath, 'src')
    copytree(sourcepath, fd['src'], ignore=shutil.ignore_patterns('.DS_Store'))

    # Create makefile in the utils/mf5to6/pymake folder
    print('Creating mf5to6 makefile')
    with cwd(os.path.join(srcpath, 'pymake')):
        pymake.main(os.path.join('..', 'src'), name, 'gfortran', 'gcc',
                    makeclean=True, dryrun=True, include_subdirs=True,
                    makefile=True, extrafiles='extrafiles.txt')
        os.path.isfile('makefile')

    # Copy makefile to utils/mf5to6/make folder
    print('Copying mf5to6 makefile')
    makefile = os.path.join(srcpath, 'pymake', 'makefile')
    d = os.path.join(srcpath, 'make', 'makefile')
    print('  {} ===> {}'.format(makefile, d))
    shutil.copyfile(makefile, d)

    # Copy makefile to distribution/xxx/utils/mf5to6/make folder
    d = os.path.join(fd['make'], 'makefile')
    print('  {} ===> {}'.format(makefile, d))
    shutil.copyfile(makefile, d)

    # Remove the makefile from the pymake folder
    os.remove(makefile)

    # Copy the Visual Studio project file
    flist = [os.path.join(srcpath, 'msvs', 'mf5to6.vfproj')]
    print('Copying mf5to6 msvs files')
    for d in flist:
        print('  {} ===> {}'.format(d, fd['msvs']))
        shutil.copy(d, fd['msvs'])
    print('\n')

    # build the executable
    exename = 'mf5to6'
    target = os.path.join(exepath, exename)
    if win_target_os:
        fc = 'ifort'
        cc = 'cl'
        exename += '.exe'
    else:
        fc = 'gfortran'
        cc = 'gcc'
    extrafiles = os.path.join(srcpath, 'pymake', 'extrafiles.txt')
    pymake.main(fd['src'], target, fc, cc, makeclean=True,
                include_subdirs=True, extrafiles=extrafiles)
    if win_target_os:
        target += '.exe'
    if not os.path.isfile(target):
        raise Exception('Did not build target: {}'.format(target))

    return


def delete_files(files, pth, allow_failure=False):
    for file in files:
        fpth = os.path.join(pth, file)
        try:
            print('removing...{}'.format(file))
            os.remove(fpth)
        except:
            print('could not remove...{}'.format(file))
            if not allow_failure:
                return False
    return True


def run_command(argv, pth, timeout=10):
    buff = ''
    ierr = 0
    with subprocess.Popen(argv,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=pth) as process:
        try:
            output, unused_err = process.communicate(timeout=timeout)
            buff = output.decode('utf-8')
        except subprocess.TimeoutExpired:
            process.kill()
            output, unused_err = process.communicate()
            buff = output.decode('utf-8')
            ierr = 100
        except:
            output, unused_err = process.communicate()
            buff = output.decode('utf-8')
            ierr = 101

    return buff, ierr


def clean_latex_files():

    print('Cleaning latex files')
    exts = ['pdf', 'aux', 'bbl', 'idx',
            'lof', 'out', 'toc']
    pth = os.path.join('..', 'doc', 'mf6io')
    files = ['mf6io.{}'.format(e) for e in exts]
    delete_files(files, pth, allow_failure=True)
    assert not os.path.isfile(pth + '.pdf')

    pth = os.path.join('..', 'doc', 'ReleaseNotes')
    files = ['ReleaseNotes.{}'.format(e) for e in exts]
    delete_files(files, pth, allow_failure=True)
    assert not os.path.isfile(pth + '.pdf')

    pth = os.path.join('..', 'doc', 'zonebudget')
    files = ['zonebudget.{}'.format(e) for e in exts]
    delete_files(files, pth, allow_failure=True)
    assert not os.path.isfile(pth + '.pdf')

    pth = os.path.join('..', 'doc', 'ConverterGuide')
    files = ['converter_mf5to6.{}'.format(e) for e in exts]
    delete_files(files, pth, allow_failure=True)
    assert not os.path.isfile(pth + '.pdf')

    pth = os.path.join('..', '..', 'modflow6-docs.git', 'mf6suptechinfo')
    files = ['converter_mf5to6.{}'.format(e) for e in exts]
    delete_files(files, pth, allow_failure=True)
    assert not os.path.isfile(pth + '.pdf')

    return


def rebuild_tex_from_dfn():

    npth = os.path.join('..', 'doc', 'mf6io', 'mf6ivar')
    pth = './'

    with cwd(npth):

        # get list of TeX files
        files = [f for f in os.listdir('tex') if
                 os.path.isfile(os.path.join('tex', f))]
        for f in files:
            fpth = os.path.join('tex', f)
            os.remove(fpth)

        # run python
        argv = ['python', 'mf6ivar.py']
        buff, ierr = run_command(argv, pth)
        msg = '\nERROR {}: could not run {} with {}'.format(ierr, argv[0],
                                                            argv[1])
        assert ierr == 0, buff + msg

        # get list for dfn files
        dfnfiles = [os.path.splitext(f)[0] for f in os.listdir('dfn') if
                    os.path.isfile(os.path.join('dfn', f)) and
                    'dfn' in os.path.splitext(f)[1]]
        texfiles = [os.path.splitext(f)[0] for f in os.listdir('tex') if
                    os.path.isfile(os.path.join('tex', f)) and
                    'tex' in os.path.splitext(f)[1]]
        missing = ''
        icnt = 0
        for f in dfnfiles:
            if 'common' in f:
                continue
            fpth = '{}-desc'.format(f)
            if fpth not in texfiles:
                icnt += 1
                missing += '  {:3d} {}.tex\n'.format(icnt, fpth)
        msg = '\n{} TeX file(s) are missing. '.format(icnt) + \
              'Missing files:\n{}'.format(missing)
        assert icnt == 0, msg

    return


def update_mf6io_tex_files(distfolder, mf6pth, expth=None):

    texpth = '../doc/mf6io'
    fname1 = os.path.join(texpth, 'mf6output.tex')
    fname2 = os.path.join(texpth, 'mf6noname.tex')
    fname3 = os.path.join(texpth, 'mf6switches.tex')
    #mf6pth = os.path.join(distfolder, 'bin', 'mf6.exe')
    #mf6pth = os.path.abspath(mf6pth)
    local = False
    if expth is None:
        local = True
        expth = os.path.join(distfolder, 'examples', 'ex01-twri')
    expth = os.path.abspath(expth)

    assert os.path.isfile(mf6pth), '{} does not exist'.format(mf6pth)
    assert os.path.isdir(expth), '{} does not exist'.format(expth)

    # run an example model
    if local:
        if os.path.isdir('./temp'):
            shutil.rmtree('./temp')
        shutil.copytree(expth, './temp')
    cmd = [os.path.abspath(mf6pth)]
    if local:
        simpth = './temp'
    else:
        simpth = expth
    buff, ierr = run_command(cmd, simpth)
    lines = buff.split('\r\n')
    with open(fname1, 'w') as f:
        f.write('{}\n'.format('{\\small'))
        f.write('{}\n'.format('\\begin{lstlisting}[style=modeloutput]'))
        for line in lines:
            f.write(line.rstrip() + '\n')
        f.write('{}\n'.format('\\end{lstlisting}'))
        f.write('{}\n'.format('}'))

    # run model without a namefile present
    if os.path.isdir('./temp'):
        shutil.rmtree('./temp')
    os.mkdir('./temp')
    cmd = [os.path.abspath(mf6pth)]
    buff, ierr = run_command(cmd, './temp')
    lines = buff.split('\r\n')
    with open(fname2, 'w') as f:
        f.write('{}\n'.format('{\\small'))
        f.write('{}\n'.format('\\begin{lstlisting}[style=modeloutput]'))
        for line in lines:
            f.write(line.rstrip() + '\n')
        f.write('{}\n'.format('\\end{lstlisting}'))
        f.write('{}\n'.format('}'))

    # run mf6 command with -h to show help
    cmd = [os.path.abspath(mf6pth), '-h']
    buff, ierr = run_command(cmd, './temp')
    lines = buff.split('\r\n')
    with open(fname3, 'w') as f:
        f.write('{}\n'.format('{\\small'))
        f.write('{}\n'.format('\\begin{lstlisting}[style=modeloutput]'))
        for line in lines:
            f.write(line.rstrip() + '\n')
        f.write('{}\n'.format('\\end{lstlisting}'))
        f.write('{}\n'.format('}'))

    # clean up
    if os.path.isdir('./temp'):
        shutil.rmtree('./temp')

    return


def build_latex_docs():
    print('Building latex files')
    pth1 = os.path.join('..', 'doc')
    pth2 = os.path.join('..', '..', 'modflow6-docs.git')
    doclist = [
               (pth1, 'mf6io', 'mf6io.tex'),
               (pth1, 'ReleaseNotes', 'ReleaseNotes.tex'),
               (pth1, 'zonebudget', 'zonebudget.tex'),
               (pth1, 'ConverterGuide', 'converter_mf5to6.tex'),
               (pth2, 'mf6suptechinfo', 'mf6suptechinfo.tex'),
              ]

    # copy version.tex from doc to modflow6-docs
    shutil.copy(os.path.join(pth1, 'version.tex'), pth2)

    for p, d, t in doclist:

        dirname = os.path.join(p, d)
        with cwd(dirname):

            cmd = ['pdflatex', t]
            buff, ierr = run_command(cmd, './')
            msg = '\nERROR {}: could not run {} on {}'.format(ierr, cmd[0],
                                                              cmd[1])
            assert ierr == 0, buff + msg

            cmd = ['bibtex', os.path.splitext(t)[0] + '.aux']
            buff, ierr = run_command(cmd, './')
            msg = '\nERROR {}: could not run {} on {}'.format(ierr, cmd[0],
                                                              cmd[1])
            assert ierr == 0, buff + msg

            cmd = ['pdflatex', t]
            buff, ierr = run_command(cmd, './')
            msg = '\nERROR {}: could not run {} on {}'.format(ierr, cmd[0],
                                                              cmd[1])
            assert ierr == 0, buff + msg

            cmd = ['pdflatex', t]
            buff, ierr = run_command(cmd, './')
            msg = '\nERROR {}: could not run {} on {}'.format(ierr, cmd[0],
                                                              cmd[1])
            assert ierr == 0, buff + msg

            fname = os.path.splitext(t)[0] + '.pdf'
            assert os.path.isfile(fname), 'Could not find ' + fname

    return


def update_latex_releaseinfo(examples_folder):

    pth = os.path.join('..', 'doc', 'ReleaseNotes')
    files = ['example_items.tex', 'example_table.tex', 'folder_struct.tex']
    delete_files(files, pth, allow_failure=True)

    # make release notes example_items.tex
    fname = os.path.join(pth, 'example_items.tex')
    examples_setup.make_example_items(fname)

    # make release notes example_table.tex
    fname = os.path.join(pth, 'example_table.tex')
    examples_setup.make_example_table(fname, examples_folder)

    cmd = ['python', 'mk_folder_struct.py']
    buff, ierr = run_command(cmd, pth)
    msg = '\nERROR {}: could not run {} on {}'.format(ierr, cmd[0],
                                                      cmd[1])
    assert ierr == 0, buff + msg

    for f in files:
        assert os.path.isfile(os.path.join(pth, f)), 'File does not exist: ' + f

    return


if __name__ == '__main__':

    # setup paths and folder structure
    win_target_os = True
    name = 'MODFLOW 6'
    exename = 'mf6'
    destpath = '.'
    versiontexname = os.path.join('..', 'doc', 'version.tex')
    version, versiondate =  get_distribution_info(versiontexname)
    distfolder = os.path.join(destpath, version)
    subdirs = ['bin', 'doc', 'examples', 'src', 'srcbmi', 'msvs', 'make', 'utils']
    fd = setup(name, destpath, version, subdirs)

    # Copy the Visual Studio solution and project files
    flist = [
             os.path.join('..', 'msvs', 'mf6.sln'),
             os.path.join('..', 'msvs', 'mf6.vfproj'),
             os.path.join('..', 'msvs', 'mf6core.vfproj'),
             os.path.join('..', 'msvs', 'mf6bmi.sln'),
             os.path.join('..', 'msvs', 'mf6bmi.vfproj'),
             ]
    print('Copying msvs files')
    for d in flist:
        print('  {} ===> {}'.format(d, fd['msvs']))
        shutil.copy(d, fd['msvs'])
    print('\n')

    # copy source folder
    copytree(os.path.join('..', 'src'), fd['src'],
             ignore=shutil.ignore_patterns('.DS_Store'))

    # copy srcbmi folder
    copytree(os.path.join('..', 'srcbmi'), fd['srcbmi'],
             ignore=shutil.ignore_patterns('.DS_Store'))

    # Create makefile in the make folder and then copy into distribution
    print('Creating makefile')
    makedir = os.path.join('..', 'make')
    makefile = os.path.join(makedir, 'makefile')
    if os.path.isfile(makefile):
        os.remove(makefile)
    with cwd(makedir):
        pymake.main(os.path.join('..', 'src'), 'mf6', 'gfortran', 'gcc',
                    makeclean=True, dryrun=True, include_subdirs=True,
                    makefile=True, extrafiles=None)
    print('  {} ===> {}'.format(makefile, fd['make']))
    shutil.copy(makefile, fd['make'])

    # build MODFLOW 6 executable
    srcdir = fd['src']
    target = os.path.join(fd['bin'], exename)
    if win_target_os:
        fc = 'ifort'
        cc = 'cl'
    else:
        fc = 'gfortran'
        cc = 'gcc'
    pymake.main(srcdir, target, fc, cc, makeclean=True, include_subdirs=True)
    if win_target_os:
        target += '.exe'
    if not os.path.isfile(target):
        raise Exception('Did not build target: {}'.format(target))

    # setup zone budget
    make_zonebudget(os.path.join('..', 'utils', 'zonebudget'), fd['utils'],
                    win_target_os, fd['bin'])

    # setup mf5to6
    make_mf5to6(os.path.join('..', 'utils', 'mf5to6'), fd['utils'],
                win_target_os, fd['bin'])

    # setup the examples
    expath = fd['examples']
    exsrcpath = os.path.join('..', '..', 'modflow6-testmodels.git', 'mf6')
    assert os.path.isdir(exsrcpath)
    examples_setup.setup_examples(exsrcpath, expath,
                                  win_target_os=win_target_os)

    # Clean and then remake latex docs
    clean_latex_files()
    rebuild_tex_from_dfn()
    update_mf6io_tex_files(distfolder, target)
    update_latex_releaseinfo(fd['examples'])
    build_latex_docs()

    # docs
    docsrc = os.path.join('..', 'doc')
    doclist = [
               [os.path.join(docsrc, 'ReleaseNotes', 'ReleaseNotes.pdf'), 'release.pdf'],
               [os.path.join(docsrc, 'mf6io', 'mf6io.pdf'), 'mf6io.pdf'],
               [os.path.join(docsrc, 'ConverterGuide', 'converter_mf5to6.pdf'), 'mf5to6.pdf'],
               [os.path.join('..', 'doc', 'zonebudget', 'zonebudget.pdf'), 'zonebudget.pdf'],
               [os.path.join('..', '..', 'modflow6-docs.git', 'mf6suptechinfo', 'mf6suptechinfo.pdf'), 'mf6suptechinfo.pdf'],
               ]

    print('Copying documentation')
    for din, dout in doclist:
        dst = os.path.join(fd['doc'], dout)
        print('  copying {} ===> {}'.format(din, dst))
        shutil.copy(din, dst)
    print('\n')

    print('Downloading published reports for inclusion in distribution')
    for url in ['https://pubs.usgs.gov/tm/06/a57/tm6a57.pdf',
                'https://pubs.usgs.gov/tm/06/a55/tm6a55.pdf',
                'https://pubs.usgs.gov/tm/06/a56/tm6a56.pdf',
                'https://github.com/MODFLOW-USGS/modflow6-testmodels/releases/download/6.1.0/csubexamples.pdf',
                ]:
        print('  downloading {}'.format(url))
        download_and_unzip(url, pth=fd['doc'], delete_zip=False, verify=False)
    print('\n')

    # Prior to zipping, enforce os line endings on all text files
    windows_line_endings = True
    convert_line_endings(distfolder, windows_line_endings)

    # Zip the distribution
    uflag = 'u'
    if win_target_os:
        uflag = ''
    zipname = version + uflag + '.zip'
    if os.path.exists(zipname):
        print('Removing existing file: {}'.format(zipname))
        os.remove(zipname)
    print('Creating zipped file: {}'.format(zipname))
    zipdir(distfolder, zipname)
    print('\n')

    print('Done...')
    print('\n')


