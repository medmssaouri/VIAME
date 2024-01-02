#!/usr/bin/env python

import sys
import os
import shutil
import argparse
import glob

# Main Function
if __name__ == "__main__" :

    parser = argparse.ArgumentParser(description="Perform a filtering action on a csv",
       formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-i", dest="input_file", default="",
      help="Input file or glob pattern to process")

    parser.add_argument("--consolidate-ids", dest="consolidate_ids", action="store_true",
      help="Use a ball tree for the searchable index")

    parser.add_argument("--decrease-fid", dest="decrease_fid", action="store_true",
      help="Use a ball tree for the searchable index")

    parser.add_argument("--increase-fid", dest="increase_fid", action="store_true",
      help="Use a ball tree for the searchable index")

    parser.add_argument("--assign-uid", dest="assign_uid", action="store_true",
      help="Assign unique detection ids to all entries in volume")

    parser.add_argument("--filter-single", dest="filter_single", action="store_true",
      help="Filter single state tracks")

    parser.add_argument("--print-types", dest="print_types", action="store_true",
      help="Print unique list of target types")

    parser.add_argument("--track-count", dest="track_count", action="store_true",
      help="Print total number of tracks")

    parser.add_argument("--average-box-size", dest="average_box_size", action="store_true",
      help="Print average box size per type")

    parser.add_argument("--conf-threshold", dest="conf_threshold", type=float, default="-1.0",
      help="Confidence threshold")

    parser.add_argument("--type-threshold", dest="type_threshold", type=float, default="-1.0",
      help="Confidence threshold")

    parser.add_argument("--print-filtered", dest="print_filtered", action="store_true",
      help="Print out tracks that were filtered out")

    parser.add_argument("--lower-fid", dest="lower_fid", type=int, default="0",
      help="Lower FID if adjusting FIDs to be within some range")

    parser.add_argument("--upper-fid", dest="upper_fid", type=int, default="0",
      help="Lower FID if adjusting FIDs to be within some range")

    parser.add_argument("--replace-file", dest="replace_file", default="",
      help="If set, replace all types in this file given their synonyms")

    args = parser.parse_args()

    input_files = []

    if len( args.input_file ) == 0:
        print( "No valid input files provided, exiting." )
        sys.exit(0)

    if '*' in args.input_file:
        input_files = glob.glob( args.input_file )
    else:
        input_files.append( args.input_file )

    id_counter = 1
    type_counts = dict()
    type_sizes = dict()
    repl_dict = dict()

    track_counter = 0
    state_counter = 0

    if args.replace_file:
        fin = open( args.replace_file, 'r' )
        if not fin:
            print( "Replace file: " + args.replace_file + " does not exist" )
        for line in fin:
            parsed = line.split( ',' )
            if len( line ) > 1:
                repl_dict[ parsed[0].rstrip() ] = parsed[1].rstrip()
            elif len( line.rstrip() ) > 0:
                print( "Error parsing line: " + line )
        fin.close()

    for input_file in input_files:
        print( "Processing " + input_file )

        fin = open( input_file, "r" )
        output = []

        id_mappings = dict()
        id_states = dict()
        unique_ids = set()
        printed_ids = set()

        for line in fin:
            if len( line ) > 0 and line[0] == '#' or line[0:9] == 'target_id':
                continue
            parsed_line = line.rstrip().split(',')
            if len( parsed_line ) < 2:
                continue
            if args.conf_threshold > 0 and len( parsed_line ) > 7:
                if float( parsed_line[7] ) < args.conf_threshold:
                    if args.print_filtered and parsed_line[0] not in printed_ids:
                        print( "Id: " + parsed_line[0] + " filtered" )
                        printed_ids.add( parsed_line[0] )
                    continue
            if args.type_threshold > 0:
                if len( parsed_line ) < 11:
                    continue
                if float( parsed_line[10] ) < args.type_threshold:
                    if args.print_filtered and parsed_line[0] not in printed_ids:
                        print( "Id: " + parsed_line[0] + " filtered" )
                        printed_ids.add( parsed_line[0] )
                    continue
            if args.track_count:
                state_counter = state_counter + 1
                if parsed_line[0] not in unique_ids:
                    unique_ids.add( parsed_line[0] )
            if args.consolidate_ids:
                parsed_line[0] = str( 100 * int( int( parsed_line[0] ) / 100 ) )
            if args.decrease_fid:
                parsed_line[2] = str( int( parsed_line[2] ) - 1 )
            if args.increase_fid:
                parsed_line[2] = str( int( parsed_line[2] ) + 1 )
            if args.lower_fid > 0:
                if int( parsed_line[2] ) < args.lower_fid:
                    continue
                parsed_line[2] = str( int( parsed_line[2] ) - args.lower_fid )
            if args.upper_fid > 0:
                if int( parsed_line[2] ) > args.upper_fid - args.lower_fid:
                    continue
            if args.assign_uid:
                if parsed_line[0] in id_mappings:
                    parsed_line[0] = id_mappings[ parsed_line[0] ]
                    has_non_single = True
                else:
                    id_mappings[parsed_line[0]] = str(id_counter)
                    parsed_line[0] = str(id_counter)
                    id_counter = id_counter + 1
            if args.filter_single:
                if parsed_line[0] not in id_states:
                    id_states[ parsed_line[0] ] = 1
                else:
                    id_states[ parsed_line[0] ] = id_states[ parsed_line[0] ] + 1
                    has_non_single = True
            if len( parsed_line ) > 9:
                top_category = ""
                top_score = -100.0
                attr_start = -1
                for i in range( 9, len( parsed_line ), 2 ):
                    if parsed_line[i][0] == '(':
                        attr_start = i
                        break
                    score = float( parsed_line[i+1] )
                    if score > top_score:
                        top_category = parsed_line[i]
                        top_score = score
                if args.print_types or args.average_box_size:
                    if top_category in type_counts:
                        type_counts[ top_category ] += 1
                    else:
                        type_counts[ top_category ] = 1
                if args.average_box_size:
                    box_width = float( parsed_line[5] ) - float( parsed_line[3] )
                    box_height = float( parsed_line[6] ) - float( parsed_line[4] )
                    if top_category in type_sizes:
                        type_sizes[ top_category ] += ( box_width * box_height )
                    else:
                        type_sizes[ top_category ] = ( box_width * box_height )
                if args.replace_file:
                    new_cat = repl_dict[ top_category ] if top_category in repl_dict else top_category
                    new_score = str(1.0)
                    parsed_line[9] = new_cat
                    parsed_line[10] = new_score
                    if attr_start > 0:
                        attr_count = len( parsed_line ) - attr_start
                        for i in range( attr_count ):
                            parsed_line[ i + 11 ] = parsed_line[ i + attr_start ]
                        parsed_line = parsed_line[ :(11+attr_count) ]
                    elif len( parsed_line ) > 11:
                        parsed_line = parsed_line[ :11 ]
            output.append( ','.join( parsed_line ) + '\n' )
        fin.close()

        if args.track_count:
           track_counter = track_counter + len( unique_ids )

        if ( args.assign_uid or args.filter_single ) and not has_non_single:
            print( "Sequence " + input_file + " has all single states" )

        if args.filter_single:
            output = [ e for e in output if id_states[ e.split(',')[ 0 ] ] > 1 ]

        if args.filter_single or args.increase_fid or args.decrease_fid \
          or args.assign_uid or args.consolidate_ids or args.filter_single \
          or args.lower_fid or args.upper_fid or args.replace_file: 
            fout = open( input_file, "w" )
            for line in output:
                fout.write( line )
            fout.close()

    if args.track_count:
        print( "Track count: " + str(track_counter) + " , states = " + str(state_counter) )

    if args.print_types:
        print( ','.join( type_counts.keys() ) )

    if args.average_box_size:
        print( "Type - Average Box Area - Total Count" )
        for i in type_sizes:
            size_str = str( float( type_sizes[ i ] ) / type_counts[ i ] )
            print( i + " " + size_str + " " + str( type_counts[ i ] ) )
