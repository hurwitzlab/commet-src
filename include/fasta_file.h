/*
 * Contributors :
 *   Pierre PETERLONGO, pierre.peterlongo@inria.fr [12/06/13]
 *   Nicolas MAILLET, nicolas.maillet@inria.fr     [12/06/13]
 *   Guillaume Collet, guillaume@gcollet.fr        [27/05/14]
 *
 * This software is a computer program whose purpose is to find all the
 * similar reads between two set of NGS reads. It also provide a similarity
 * score between the two samples.
 *
 * Copyright (C) 2014  INRIA
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __FASTA_FILE_H__
#define __FASTA_FILE_H__

#include "read_file.h"

#include <fstream>
#include <zlib.h>

////////////////////////////////////////////////////////////
// This class is used to read a FASTA file
//
class FastaFile : public ReadFile
{
private:
	std::ifstream infile;
	std::string tmp_str;
	
public:
	
	////////////////////////////////////////////////////////////
	// Open the file, count reads and set boolean vector to 1
	//
	explicit FastaFile (const std::string & file_name)
	{
		//std::cerr << "Open FASTA\n";
		fname = file_name;
		// Open the file
		infile.open (file_name.c_str());
		if (!infile.good()) {
			std::cerr << "Error: Cannot open Fasta File " << file_name << "\n";
			exit(1);
		}
		// Count reads
		//const clock_t begin_time = clock();
		nb_reads = 0;
		while (infile.good()) {
			getline (infile, tmp_str);
			try {
				if (tmp_str.at(0) == '>')
					nb_reads++;
			} catch (std::exception & e) {}
		}
		rewind();
		//std::cerr << "Count " << nb_reads << " reads in " << float( clock () - begin_time ) / CLOCKS_PER_SEC << " s\n";
		// Set boolean vector to 1
		bv.init_true(nb_reads);
		current_read_pos = 0;
		_nb_valid_reads = bv.nb_one();
		_cnt_valid_reads = 0;
		first_read = true;
	}
	
	
	////////////////////////////////////////////////////////////
	// Open the file, count reads and read boolean vector in bv file
	// + check boolean vector size and nb_reads are equal
	//
	explicit FastaFile (const std::string & file_name, const std::string & bv_file_name)
	{
		fname = file_name;
		// Open the file
		infile.open (file_name.c_str());
		if (!infile.good()) {
			std::cerr << "Error: Cannot open Fastq File " << file_name << "\n";
			exit(1);
		}
		// Count reads
		//const clock_t begin_time = clock();
		nb_reads = 0;
		while (infile.good()) {
			getline (infile, tmp_str);
			try {
				if (tmp_str.at(0) == '>')
					nb_reads++;
			} catch (std::exception & e) {}
		}
		rewind();
		//std::cerr << "Count " << nb_reads << " reads in " << float( clock () - begin_time ) / CLOCKS_PER_SEC << " s\n";
		// Read the boolean vector in bv file
		bv.read(bv_file_name);
		// Check boolean vector size and nb_reads are equal
		if (nb_reads != bv.size()) {
			std::cerr << "Number of reads in " << file_name << " and boolean vector size are not equal -> quit\n";
			exit(1);
		}
		_nb_valid_reads = bv.nb_one();
		_cnt_valid_reads = 0;
		current_read_pos = 0;
		first_read = true;
	}
	
	
	////////////////////////////////////////////////////////////
	// Destructor only closes the file
	//
	~FastaFile ()
	{
		infile.close();
	}
	
	
	////////////////////////////////////////////////////////////
	// get_next_read returns the next read in the file
	// OR an empty string if no more read is available
	//
	std::string & get_next_read ()
	{
		// clear data and increment the position
		if (first_read) {
			first_read = false;
		} else {
			current_read_pos++;
		}
		current_read_data.clear();
		current_read_seq.clear();
		
		if (_cnt_valid_reads < _nb_valid_reads) {
			// While reads are not valid in the boolean vector, flush them
			while (current_read_pos < nb_reads && infile.good()) {
				if (!bv.is_set(current_read_pos)) {
					flush_next_read ();
					current_read_pos++;
				} else {
					break;
				}
			}
			// The current read is 1 in the boolean vector
			// Or current_read_pos >= nb_reads -> end of file
			if (current_read_pos < nb_reads) {
				if (infile.good()) {
					getline (infile, tmp_str);
					if (tmp_str[0] != '>') {
						std::cerr << "Error in Fasta format !!\n";
						exit(1);
					}
					if (tmp_str[tmp_str.size() - 1] == '\n' ) {
						tmp_str.erase(tmp_str.size() - 1);
					}
					current_read_data += tmp_str + "\n";
					while (infile.good() && infile.peek() != '>' && infile.peek() != (int) std::char_traits<wchar_t>::eof()) {
						getline (infile, tmp_str);
						if (!tmp_str.empty()) {
							if (tmp_str[tmp_str.size() - 1] == '\n' ) {
								tmp_str.erase(tmp_str.size() - 1);
							}
							current_read_seq += tmp_str;
							current_read_data += tmp_str + "\n";
						}
					}
				}
			}
			if (!current_read_seq.empty()) {
				_cnt_valid_reads++;
			}
		}
		return current_read_seq;
	}
	
	
	////////////////////////////////////////////////////////////
	// Just read the next read without storing it
	//
	void flush_next_read () {
		current_read_data.clear();
		current_read_seq.clear();
		if (infile.good()) {
			getline (infile, tmp_str);
		}
		if (tmp_str[0] != '>') {
			std::cerr << "Error in Fasta format !!\n";
			exit(1);
		}
		while (infile.good() && infile.peek() != '>') {
			getline (infile, tmp_str);
		}
	}
	
	
	////////////////////////////////////////////////////////////
	// Return the full FASTQ entry of the current read
	//
	const std::string & get_data() const
	{
		return current_read_data;
	}
	
	
	////////////////////////////////////////////////////////////
	// Return the sequence of the current read
	//
	const std::string & get_read() const
	{
		return current_read_seq;
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the current read to 1 in the boolean vector
	//
	void tag_current_read ()
	{
		bv.set(current_read_pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the current read to 0 in the boolean vector
	//
	void untag_current_read ()
	{
		bv.unset(current_read_pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the read at pos to 1 in the boolean vector
	//
	void tag (const unsigned long & pos)
	{
		bv.set(pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the read at pos to 0 in the boolean vector
	//
	void untag (const unsigned long & pos)
	{
		bv.unset(pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Go to the beginning of the file -> current_read_pos = -1
	// because no read has been read
	//
	void rewind () {
		infile.clear();
		infile.seekg(0);
		_cnt_valid_reads = 0;
		current_read_pos = 0;
		first_read = true;
	};
	
	////////////////////////////////////////////////////////////
	// Set the comment of the boolean vector
	//
	void set_bv_comment (const std::string & str)
	{
		bv.set_comment(str);
	}
	
	////////////////////////////////////////////////////////////
	// Save the boolean vector in the given file name
	//
	void save_bv (const std::string & file_name)
	{
		bv.print(file_name);
	}
	
	////////////////////////////////////////////////////////////
	// Save the boolean vector in fname.bv
	//
	void save_bv ()
	{
		bv.print(fname + ".bv");
	}
	
	////////////////////////////////////////////////////////////
	// Save the selected reads in a given file name
	//
	void save (const std::string & directory, const std::string & suffix) {
		std::string output_file_name = directory + "/" + fname.substr(fname.rfind("/") + 1)  + "_in_" + suffix+ ".fa";
		rewind();
		std::ofstream outfile;
		outfile.open (output_file_name.c_str());
		if (!outfile.good()) {
			std::cerr << "Cannot write on file " << output_file_name << "\n";
			exit(1);
		}
		std::string & current_read = get_next_read();
		while (!current_read.empty()) {
			outfile << get_data();
			current_read = get_next_read();
		}
		outfile.close();
	}
};

class GzFastaFile : public ReadFile
{
private:
	gzFile infile;
	static const int NORMALSIZEREAD = 1048576;
	char tmp_str[NORMALSIZEREAD];
public:
	GzFastaFile (const std::string & file_name)  {
		//std::cerr << "Add Gzip Fasta File " << file_name << "\n";
		fname = file_name;
		// Open the file
		infile = (gzFile) gzopen (file_name.c_str(), "r");
		if (infile == NULL) {
			std::cerr << "Error: Cannot open Fasta File " << file_name << "\n";
			exit(1);
		}
		// Count reads
		//const clock_t begin_time = clock();
		nb_reads = 0;
		while (gzgets(infile, tmp_str, NORMALSIZEREAD) != NULL) {
			if (tmp_str[0] == '>') {
				nb_reads++;
			}
		}
		rewind();
		//std::cerr << "Count " << nb_reads << " reads in " << float( clock () - begin_time ) / CLOCKS_PER_SEC << " s\n";
		// Set boolean vector to 1
		bv.init_true(nb_reads);
		current_read_pos = 0;
		_nb_valid_reads = bv.nb_one();
		_cnt_valid_reads = 0;
		first_read = true;

	}
	
	GzFastaFile (const std::string & file_name, const std::string & bv_file_name)  {
		//std::cerr << "Add Gzip Fasta File " << file_name << " with bv " << bv_file_name << "\n";
		fname = file_name;
		// Open the file
		infile = (gzFile) gzopen (file_name.c_str(), "r");
		if (infile == NULL) {
			std::cerr << "Error: Cannot open Fasta File " << file_name << "\n";
			exit(1);
		}
		// Count reads
		//const clock_t begin_time = clock();
		nb_reads = 0;
		while (gzgets(infile, tmp_str, NORMALSIZEREAD) != NULL) {
			if (tmp_str[0] == '>') {
				nb_reads++;
			}
		}
		rewind();
		//std::cerr << "Count " << nb_reads << " reads in " << float( clock () - begin_time ) / CLOCKS_PER_SEC << " s\n";
		// Read the boolean vector in bv file
		bv.read(bv_file_name);
		// Check boolean vector size and nb_reads are equal
		if (nb_reads != bv.size()) {
			std::cerr << "Number of reads in " << file_name << " and boolean vector size are not equal -> quit\n";
			exit(1);
		}
		current_read_pos = 0;
		_nb_valid_reads = bv.nb_one();
		_cnt_valid_reads = 0;
		first_read = true;
	}
	
	~GzFastaFile ()
	{
		gzclose(infile);
	}
	
	////////////////////////////////////////////////////////////
	// get_next_read returns the next read in the file
	// OR an empty string if no more read is available
	//
	std::string & get_next_read ()
	{
		// clear data and increment the position
		if (first_read) {
			first_read = false;
		} else {
			current_read_pos++;
		}
		current_read_data.clear();
		current_read_seq.clear();
		
		if (_cnt_valid_reads < _nb_valid_reads) {
			// While reads are not valid in the boolean vector, flush them
			while (current_read_pos < nb_reads && !gzeof(infile)) {
				if (!bv.is_set(current_read_pos)) {
					flush_next_read ();
					current_read_pos++;
				} else {
					break;
				}
			}
			// The current read is 1 in the boolean vector
			// Or current_read_pos >= nb_reads -> end of file
			if (current_read_pos < nb_reads) {
				if (!gzeof(infile)) {
					if(gzgets(infile, tmp_str, NORMALSIZEREAD) != NULL) {
						if (tmp_str[0] != '>') {
							std::cerr << "Error in Fasta format !!\n";
							exit(1);
						}
						current_read_data += std::string(tmp_str);
						if (current_read_data[current_read_data.size() - 1] != '\n') {
							current_read_data += '\n';
						}
						char c = gzgetc(infile);
						while (!gzeof(infile) && c != '>') {
							if (c != '\n') {
								current_read_seq += c;
							}
							current_read_data += c;
							c = gzgetc(infile);
						}
						gzungetc(c, infile);
					}
				}
			}
			if (!current_read_seq.empty()) {
				_cnt_valid_reads++;
			}
		}
		return current_read_seq;
	}
	
	
	////////////////////////////////////////////////////////////
	// Just read the next read without storing it
	//
	void flush_next_read () {
		current_read_data.clear();
		current_read_seq.clear();
		if (gzgets(infile, tmp_str, NORMALSIZEREAD) != NULL) {
			if (tmp_str[0] != '>') {
				std::cerr << "Error in Fasta format !!\n";
				exit(1);
			}
			char c = gzgetc(infile);
			while (!gzeof(infile) && c != '>') {
				gzungetc(c, infile);
				gzgets(infile, tmp_str, NORMALSIZEREAD);
				c = gzgetc(infile);
			}
			gzungetc(c, infile);
		}
	}

	
	////////////////////////////////////////////////////////////
	// Return the full FASTQ entry of the current read
	//
	const std::string & get_data() const
	{
		return current_read_data;
	}
	
	
	////////////////////////////////////////////////////////////
	// Return the sequence of the current read
	//
	const std::string & get_read() const
	{
		return current_read_seq;
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the current read to 1 in the boolean vector
	//
	void tag_current_read ()
	{
		bv.set(current_read_pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the current read to 0 in the boolean vector
	//
	void untag_current_read ()
	{
		bv.unset(current_read_pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the read at pos to 1 in the boolean vector
	//
	void tag (const unsigned long & pos)
	{
		bv.set(pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Set the bit of the read at pos to 0 in the boolean vector
	//
	void untag (const unsigned long & pos)
	{
		bv.unset(pos);
	}
	
	
	////////////////////////////////////////////////////////////
	// Go to the beginning of the file -> current_read_pos = -1
	// because no read has been read
	//
	void rewind () {
		gzclose(infile);
		infile = (gzFile) gzopen (fname.c_str(), "r");
		if (infile == NULL) {
			std::cerr << "Error: Cannot open Fasta File " << fname << "\n";
			exit(1);
		}
		current_read_pos = 0;
		_cnt_valid_reads = 0;
		first_read = true;
	};
	
	////////////////////////////////////////////////////////////
	// Set the comment of the boolean vector
	//
	void set_bv_comment (const std::string & str)
	{
		bv.set_comment(str);
	}
	
	////////////////////////////////////////////////////////////
	// Save the boolean vector in the given file name
	//
	void save_bv (const std::string & file_name)
	{
		bv.print(file_name);
	}
	
	////////////////////////////////////////////////////////////
	// Save the boolean vector in fname.bv
	//
	void save_bv ()
	{
		bv.print(fname + ".bv");
	}
	
	////////////////////////////////////////////////////////////
	// Save the selected reads in a given file name
	//
	void save (const std::string & directory, const std::string & suffix) {
		std::string output_file_name = directory + "/" + fname.substr(fname.rfind("/") + 1)  + "_in_" + suffix+ ".fa.gz";
		rewind();
		gzFile filetmp = (gzFile) gzopen(output_file_name.c_str(), "w6");
		if (filetmp == NULL) {
			std::cerr << "Error, cannot open file " << output_file_name << "\n";
			exit(1);
		}
		std::string & current_read = get_next_read();
		while (!current_read.empty()) {
			gzprintf(filetmp, "%s", get_data().c_str());
			current_read = get_next_read();
		}
		gzclose(filetmp);
	}

};

#endif
