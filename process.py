"""
based of ps.py
Unzips any zips
Then allows the -subset for processing.
Basically just calls powersorter and url_gen.
"""
import sys
from zipfile import ZipFile
import powersorterRF1 as powersorter
#import url_genRF1 as url_gen
from url_genRF1 import generate_url_records_suffixes
import shutil
from pathlib import Path
import os
import glob
import csv
import re
from wand.image import Image
from collections import Counter
Problem = []

def scan_for_archives(dir):
    '''
    Scans a dir for registered archive file extensions
    Registered means Zip or anything shutil can unzip.
    '''
    result = []

    other_exts = [i[1] for i in shutil.get_unpack_formats()]
    ext_patterns = ['*' + i for g in other_exts for i in g]
    # print(ext_patterns)
    try:
        folders = [f for f in Path(dir).iterdir()]
        archives = [f for f in Path(dir).iterdir() if any(f.match(p) for p in ext_patterns)]
        not_unpackable = [f for f in Path(dir).iterdir() if not any(f.match(p) for p in ext_patterns)]
        print(f'found {len(archives)} archives to unpack out of {len(folders)} total folders')
        if not_unpackable:
            print(f'found {len(not_unpackable)} folders or archives that cannot be unpacked: {not_unpackable}')
            msg = 'could not unpack' + str(not_unpackable)
            #print(f'{msg}')
            Problem.append([msg])
        result = archives
    except:
        print(dir, 'not a valid path')

    return result

def unpack_archives(archive_paths, delete_archive=True):
    '''
    Accepts a list of folder(s) (paths?). Replaces them with unzipped folder of the same name.
    Zips it tests for corruptions then only extracts the JPG and DNG file extensions found.
    Other archive types are handled by shutil.
    '''
    result = []

    for arc in archive_paths:
        # default location is cwd, instead parse name and path out to create new folder
        loc = arc.parent
        name = arc.stem
        # ext = arc.suffixes
        new_folder = os.path.join(loc, name)
        unpacked = 0

        try:
            # if zip, just unpack JPG/DNG using ZipFile
            if arc.suffix.lower() == '.zip':
                with ZipFile(arc, 'r') as zip_object:
                    # test the archive first to see if it's corrupt
                    ret = zip_object.testzip()
                    if ret is not None:
                        print(f'First bad file in zip:', ret)
                        Problem.append(ret)
                    else:
                        print(f'Zip archive', arc, 'is good.')

                    list_names = zip_object.namelist()
                    #print(list_names)
                    # we should do a quick survey to detect simple file mismatches
                    ext_list = [i.split('.')[1].lower() for i in list_names if '.' in i]
                    #print(ext_list)
                    zip_result = zip_survey(ext_list)
                    #print(ext_list, zip_result)
                    if not ext_list:
                        msg = 'Nothing extracted from ' + name
                        print(msg)
                        Problem.append(msg)
                    elif zip_result < 0:
                        print(f'No RAW detected in archive.')
                    elif zip_result == 0:
                        msg = 'More RAW detected than expected from ' + name
                        print(msg)
                        Problem.append([msg])

                    for file_name in list_names:
                        if file_name.lower().endswith(tuple(['.jpg', '.jpeg', '.dng'])):
                            # Extract any file with these exts from zip (skip RAW)
                            zip_object.extract(file_name, arc.parent)
                            # if verbose:
                            #   print(f'Extracting', file_name)
                            unpacked = 1
            # otherwise, fallback to shutil
            else:
                try:
                    # 3.6 this can't handle path objects
                    shutil.unpack_archive(str(arc), arc.parent)
                    unpacked = 1
                except:
                    print(f"Unexpected error unpacking:", arc, sys.exc_info()[0])
            result.append(new_folder)
            # print('unpacked', new_folder)

            # remove the archive if it was unpacked
            if delete_archive and unpacked == 1:
                os.remove(arc)
            elif delete_archive and unpacked == 0:
                msg = 'Nothing was unpacked from archive named' + arc.name
                print(f"Nothing was unpacked from archive named {arc.name}.")
                Problem.append([msg])
        except ValueError:
            print(arc.stuffix, 'was not valid unpack archive type:', shutil.get_unpack_formats())
            Problem.append(ValueError)
        except:
            error = sys.exc_info()[0]
            print(f"Unexpected error:", sys.exc_info()[0])
            Problem.append(error)
            # print("Unexpected error:")
            raise

    return result

deriv_values = {
    'THUMB': {'DESIGNATOR' : '_thumb', 'SIZE' : 'x390'},
    'MED' : {'DESIGNATOR' : '_med', 'SIZE' : 'x900'}}

def generate_derivatives(path, settings):
    '''
    Takes a path, makes both deriv types from this img using wand.Image.
    Saves right back where the Orig was located.
    '''

    for k in deriv_values.keys():
        try:
            with Image(filename=path) as original:
                with original.clone() as derivative:
                    # resize height, preserve aspect ratio
                    derivative.transform(resize=deriv_values[k]['SIZE'])
                    derivative_path = os.path.join(path.parent, path.stem + deriv_values[k]['DESIGNATOR'] + path.suffix)
                    #print(f'deriv path: {derivative_path}')
                    derivative.save(filename=derivative_path)
                    if settings.verbose:
                        print(f"generated {deriv_values[k]['SIZE']}")
                    #return derivative_path
        except Exception as e:
            print('Unable to create derivative:', e)
            Problem.append(e)
            #return None

def zip_survey(inp):
    '''
    Accept a list of extensions.
    Check the RAW file count matches JPG/DNG.
    Since only these are not unpacked.
    '''
    result = -1
    raw_list = ['raw', 'nef', 'cr2']
    jpg_list = ['jpg', 'jpeg']
    # make a counter object, to get a nice dict with counts
    c = Counter(inp)
    #print(f'Zip Counter: {c}')
    # if any raw formats, do stuff
    if any(e in c.keys() for e in raw_list):
        #print(f'need to count various exts')
        # aggregate for variations of RAW files
        raw_count = sum([c[i] for i in c if i in raw_list])
        #print(f'count of raws: {raw_count}')
        # aggregate for variations of JPG format
        jpg_count = sum([c[i] for i in c if i in jpg_list])
        #print(f'count of jpgs: {jpg_count}')

        if raw_count == c['dng'] == jpg_count:
            #print(f' > Needs Derivs Generated')
            result = 1
        elif raw_count == c['dng'] == jpg_count // 3:
            #print(f' > Has Derivs Generated')
            result = 1
        elif raw_count > c['dng'] or raw_count > jpg_count:
            #print(f' > More RAW than DNG or JPG')
            result = 0
        elif raw_count < c['dng'] or raw_count < jpg_count:
            #print(f' > Less RAW than DNG or JPG')
            result = 0
        else:
            #print(f' > UNCASED RESULT 0')
            result = 0
    else:
        print(f'No RAW detected')

    return result

def ext_survey(inp):
    '''
    Accept a list of extensions.
    Test some things, try to eval if anything is missing.
    '''
    #result = []
    result = -1
    raw_list = ['raw', 'nef', 'cr2']
    jpg_list = ['jpg', 'jpeg']

    # make a counter object, to get a nice dict with counts
    c = Counter(inp)
    #print(f'ext counter: {c}')

    # if any raw formats, do stuff
    #if any(e in c.keys() for e in raw_list):
        #print(f'need to count various exts')
    # aggregate for variations of RAW files
    raw_count = sum([c[i] for i in c if i in raw_list])
    #print(f'count of raws: {raw_count}')
    # aggregate for variations of JPG format
    jpg_count = sum([c[i] for i in c if i in jpg_list])
    #print(f'count of jpgs: {jpg_count}')

    # expecting NEF/DNG/JPG
    #else:
    if len(c) == 3:
        print(f'probably the right ones?')
        if raw_count == c['dng'] == jpg_count:
            print(f' > Needs Derivs Generated')
            result = 1
        elif raw_count == c['dng'] == jpg_count // 3:
            print(f' > Has Derivs Generated')
            result = 1
        else:
            print(f' > UNCASED RESULT A')
            result = 0
    elif len(c) == 2:
        print(f'probably missing raw? (acceptable)')
        if c['dng'] == jpg_count:
            print(f' > Needs Derivs Generated')
            result = 1
        elif c['dng'] == jpg_count//3:
            print(f' > Has Derivs Generated')
            result = 1
        else:
            print(f' > UNCASED RESULT B')
            result = 0
    elif len(c) == 1:
        print(f' > probably just raw?')
        #
    else:
        print(f' > UNCASED RESULT C')
        result = 1

    return result

def main():
    # set up argparse and get arguments
    args = powersorter.arg_setup()

    config_file = args['config']
    dry_run = args['dry_run']
    verbose = args['verbose']
    force_overwrite = args['force']
    input_path_override = args['input_path']
    subset = args['subset']
    unpack = args['unpack']
    deriv = args['generate_derivatives']

    #Confirm force overwrite
    force_overwrite_confirmed = False
    if force_overwrite:
        print('Files with identical names will be overwritten if you proceed.')
        response = input('Type \'overwrite\' and [RETURN/ENTER] to confirm desire to overwrite files: ')
        if response == 'overwrite':
            print('Will overwrite duplicate file names...')
            force_overwrite_confirmed = True
        else:
            print('Overwrite not confirmed. Exiting...')
            force_overwrite_confirmed = False
            sys.exit()

    #Initialize settings with arg parameters
    settings = powersorter.Settings(dry_run=dry_run, verbose=verbose, force_overwrite=force_overwrite_confirmed)
    #Load settings from config file
    settings.load_config(config_file=config_file)

    # input_path setting in config file can be overridden using value passed in args input_path_override
    # getting path from settings isn't necessary, just here for illustration
    # if input_path isn't passed to sort, it will use settings.input_path by default
    input_path = settings.input_path
    #print(f's.inp', settings.input_path, type(settings.input_path))
    # verify path exists before starting
    #print(f'inp', input_path, type(input_path))
    try:
        os.path.isdir(input_path)
    except:
        print(f'Input_path was not valid.')

    # scan for archives
    archives = scan_for_archives(input_path)
    #print(f'archives found:', archives)
    # if any archives, unpack them
    if archives:
        #print(f'Archives found: {archives}')
        if dry_run and unpack:
            print(f'Archives would have been unpacked: {archives}')
        elif unpack:
            unpacked = unpack_archives(archives)  # , delete_archive=False
            print(f'unpacked archives: {unpacked}')
        else:
            print(f'Archives would have been unpacked if -unpack: {archives}')

    # subset based on parent folders, if flag says to
    if subset:
        print(f'Starting SUBSET process')
        # using chdir shortens the path glob returns to be SORTFOLDER/img.jpg
        orig_dir = os.getcwd()
        os.chdir(input_path)

        # this strongly supposes the files structure is /INPUT/sortable/jpg
        # would be better to iterate on path/to/sortable?
        parents = set([f.rpartition('/')[0] for f_ in [glob.glob(e, recursive = True) for e in ('./**/*.jpg', './**/*.jpeg')] for f in f_])
        print(f'subsetting on:', parents)
        # return chdir
        os.chdir(orig_dir)

        # iterate on input+parent paths and call sort, url_gen
        for p in parents:
            subset_path = os.path.join(input_path, p)

            # quick survey of contents (by ext)
            ext_list = [i.suffix.replace('.', '') for i in Path(os.path.join(input_path, subset_path)).glob('*.*')]
            print(ext_list)
            # strip the period out from .suffix
            #ext_list = ext_list.replace('.', '')
            ext_result = ext_survey(ext_list)
            #print(ext_list, ext_result)

            if deriv:
                # print(f'Somehow gen derivs for', input_path)
                # test = [f for f_ in [Path(input_path).rglob(e) for e in ('*/*.jpg', '*/*.jpeg')] for f in f_]
                # print(f'test:', test)
                # glob is not good at *not* matching stuff, like this gets all JPGs
                # single folder the */*.jpg pattern fails
                # will using rglob let this work for nested tho? seems good
                #print(Path(os.path.join(input_path, subset_path)))
                jpg_glob = [f for f_ in [Path(os.path.join(input_path, subset_path)).rglob(e) for e in ('*.jpg', '*.jpeg')] for f in f_]
                #print(f'jpg grab', jpg_glob)
                # but we could coarsely say, if there are none of these, then gen. still need regex for just the Pri JPGs.
                med_glob = [f for f_ in [Path(os.path.join(input_path, subset_path)).rglob(e) for e in ('*_med.jpg', '*_med.jpeg')] for f in f_]
                # print(f'med grab', med_glob)
                thu_glob = [f for f_ in [Path(os.path.join(input_path, subset_path)).rglob(e) for e in ('*_thumb.jpg', '*_thumb.jpeg')] for f in
                            f_]
                # print(f'thu grab', thu_glob)

                # only gen derivs if they are all missing
                if (len(med_glob) < 1 and len(med_glob) < 1):
                    print(f'both derivs req')
                    # coarse glob of ALL jpgs
                    path_jpg_pattern = re.compile('.*' + settings.catalog_number_regex + settings.web_jpg_regex)
                    needs_derivs = []
                    for i in jpg_glob:
                        # print(i)
                        # use regex to winnow glob down to just the Primary/Web JPG
                        m = path_jpg_pattern.match(str(i))
                        if m:
                            # print(m, m.groupdict())
                            needs_derivs.append(i)
                    print(f' - generating {len(needs_derivs)} x2 derivs (will take a bit)')
                    for i in needs_derivs:
                        #print(i)
                        generate_derivatives(i, settings)
                elif len(med_glob) < 1:
                    print(f' med derivs req')
                elif len(thu_glob) < 1:
                    print(f' thu derivs req')

            print(f'sorting subfolder', subset_path)
            sort_results = powersorter.sort(
                settings_obj=settings, \
                input_path=subset_path, #only diff is here \
                number_pad=settings.number_pad, \
                folder_increment=settings.folder_increment, \
                catalog_number_regex=settings.catalog_number_regex, \
                collection_prefix=settings.collection_prefix, \
                file_types=settings.file_types, \
                destination_base_path=settings.output_base_path)
            # Summary report
            if verbose:
                print(f"sorted_file_count {sort_results['sorted_file_count']}")
                print(f"unmoved_file_count {sort_results['unmoved_file_count']}")
                if sort_results['unmoved_file_count']:
                    print(f' < Leftover Files >')
                    leftover_glob = [f for f_ in [Path(input_path).rglob(e) for e in ('*.jpg', '*.jpeg')] for f in f_]
                    #print(f'left {leftover_glob}')
                    for i in leftover_glob:
                        print(f' - {i}')
            print(f'Log file written to:', sort_results['log_file_path'])
            print(f'Starting URL_GEN for the log file.')

            occurrence_set = generate_url_records_suffixes(settings=settings, input_file=sort_results['log_file_path'])
            # print(occurrence_set)
            # Get input file name
            #input_file_name_stem = Path(input_file).stem
            input_file_name_stem = Path(sort_results['log_file_path']).stem
            output_file_name = input_file_name_stem + '_urls.csv'
            print(f'Writing urls to:', output_file_name)

            with open(output_file_name, 'w', newline='') as csvfile:
                fieldnames = ['catalog_number', 'large', 'web', 'thumbnail']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for key, image_set in occurrence_set.items():
                    writer.writerow(image_set)

    else:
    # sort once
        if deriv:
            #print(f'Somehow gen derivs for', input_path)
            #test = [f for f_ in [Path(input_path).rglob(e) for e in ('*/*.jpg', '*/*.jpeg')] for f in f_]
            #print(f'test:', test)
            # glob is not good at *not* matching stuff, like this gets all JPGs
            # single folder the */*.jpg pattern fails
            # will using rglob let this work for nested tho? seems good
            jpg_glob = [f for f_ in [Path(input_path).rglob(e)for e in ('*.jpg', '*.jpeg')] for f in f_]
            #print(f'jpg grab', jpg_glob)
            # but we could coarsely say, if there are none of these, then gen. still need regex for just the Pri JPGs.
            med_glob = [f for f_ in [Path(input_path).rglob(e) for e in ('*_med.jpg', '*_med.jpeg')] for f in f_]
            #print(f'med grab', med_glob)
            thu_glob = [f for f_ in [Path(input_path).rglob(e)for e in ('*_thumb.jpg', '*_thumb.jpeg')] for f in f_]
            #print(f'thu grab', thu_glob)

            # only gen derivs if they are all missing
            if (len(med_glob) < 1 and len(med_glob) < 1):
                print(f'both derivs req')
                # coarse glob of ALL jpgs
                path_jpg_pattern = re.compile('.*' + settings.catalog_number_regex + settings.web_jpg_regex)
                needs_derivs = []
                for i in jpg_glob:
                    # print(i)
                    # use regex to winnow glob down to just the Primary/Web JPG
                    m = path_jpg_pattern.match(str(i))
                    if m:
                        # print(m, m.groupdict())
                        needs_derivs.append(i)
                print(f' - generating {len(needs_derivs)} x2 derivs (will take a bit)')
                for i in needs_derivs:
                    #print(i)
                    generate_derivatives(i, settings)
            elif len(med_glob) < 1:
                print(f' med derivs req')
            elif len(thu_glob) < 1:
                print(f' thu derivs req')

        print('STARTING sort')
        sort_results = powersorter.sort(
            settings_obj=settings, \
            input_path=input_path, \
            number_pad=settings.number_pad, \
            folder_increment=settings.folder_increment, \
            catalog_number_regex=settings.catalog_number_regex,\
            collection_prefix=settings.collection_prefix, \
            file_types=settings.file_types, \
            destination_base_path=settings.output_base_path)
        print(f'sort res: {sort_results}')

        occurrence_set = generate_url_records_suffixes(settings=settings, input_file=sort_results['log_file_path'])
        # print(occurrence_set)
        # Get input file name
        # input_file_name_stem = Path(input_file).stem
        input_file_name_stem = Path(sort_results['log_file_path']).stem
        output_file_name = input_file_name_stem + '_urls.csv'
        print(f'Writing urls to:', output_file_name)

        with open(output_file_name, 'w', newline='') as csvfile:
            fieldnames = ['catalog_number', 'large', 'web', 'thumbnail']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for key, image_set in occurrence_set.items():
                writer.writerow(image_set)

        # Summary report
        if verbose:
            print(f"sorted_file_count {sort_results['sorted_file_count']}")
            print(f"unmoved_file_count {sort_results['unmoved_file_count']}")
            # ya know, it would be nice to know more about these
        #print(sort_results['unmoved_file_count'])
        if sort_results['unmoved_file_count']:
            print(f' < Leftover Files >')
            leftover_glob = [f for f_ in [Path(input_path).rglob(e)for e in ('*.jpg', '*.jpeg')] for f in f_]
            print(f'left {leftover_glob}')
            for i in leftover_glob:
                print(f' - {i}')
        print(f'Log file written to:', sort_results['log_file_path'])
    print(f'Process COMPLETE')
    if Problem:
        print(f' < Problem listing >')
        for i in Problem:
            print(f' - {i}')

if __name__ == '__main__':
    main()