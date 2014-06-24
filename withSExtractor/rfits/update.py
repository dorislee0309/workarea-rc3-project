import montage_wrapper as montage
from astropy.io import fits as pyfits
import os
import shutil
from math import trunc
import sqlcl
import sys 
import fnmatch
# Assume you are inside directory (rfits/) where you have pulled all the g band fit files 
# find . -name "SDSS_r_*.fits" -type f -exec cp {} ./rfits \; 

def mosaic_band(band,ra,dec,margin,radius,pgc,clean=True):
    '''
    Input: source info param
    Create a mosaic fit file for the specified band.
    Return: String filename of resulting mosaic
    '''
    DEBUG = True
    filename = "{},{}".format(str(ra),str(dec))
    if (DEBUG) : print ("Querying data that lies inside margin")
    result = sqlcl.query( "SELECT distinct run,camcol,field FROM PhotoObj WHERE  ra between {0}-{1} and  {0}+{1}and dec between {2}-{3} and  {2}+{3}".format(str(ra),str(margin),str(dec),str(margin))).readlines()
    # clean_result = sqlcl.query( "SELECT distinct run,camcol,field FROM PhotoObj WHERE  CLEAN =1 and ra between {0}-{1} and  {0}+{1}and dec between {2}-{3} and  {2}+{3}".format(str(ra),str(margin),str(dec),str(margin))) .readlines()
    print (result)
    data =[]
    count =0
    for i in result:
        if count>1:
            list =i.split(',')
            list[2]= list[2][:-1]
            data.append(list)
        count += 1 
    print (data)
    if len(data)==0:
        if (DEBUG): print ('The given ra, dec of this galaxy does not lie in the SDSS footprint. Onto the next galaxy!')#Exit Program.'
        #output.write(str(ra)+ "     "+ str(dec)+"     "+str(radius)+"\n")
        #output.write("{}     {}     {}     {} \n".format(str(ra),str(dec),str(radius),pgc))
        sys.exit()
        # break
    else :
        if (DEBUG): 
            print ( "Complete Query. These data lies within margin: ")
            print (data)
    os.mkdir(filename)
    os.chdir(filename)
    os.mkdir(band)
    os.chdir(band)
    os.mkdir ("raw")
    os.mkdir ("projected")
    os.chdir("raw")
    if (DEBUG): print ("Retrieving data from SDSS SAS server for "+ band +"band")
    for i in data :  
        out = "frame-{}-{}-{}-{}".format(str(band),str(i[0]).zfill(6),str(i[1]),str(i[2]).zfill(4))
        os.system("wget http://mirror.sdss3.org/sas/dr10/boss/photoObj/frames/301/{}/{}/{}.fits.bz2".format(str(i[0]),str(i[1]),out) )
        os.system("bunzip2 {}.fits.bz2".format(out))
    os.chdir("../")
    if (DEBUG) : print("Creating mosaic for {} band.".format(band))
    montage.mImgtbl("raw","images.tbl")
    montage.mHdr("{} {}".format(str(ra),str(dec)),margin,"{}.hdr".format(out))
    if (DEBUG): print ("Reprojecting images")
    os.chdir("raw")
    montage.mProjExec("../images.tbl","../"+out+".hdr","../projected", "../stats.tbl") 
    os.chdir("..")
    montage.mImgtbl("projected","pimages.tbl")
    os.chdir("projected")
    montage.mAdd("../pimages.tbl","../"+out+".hdr","SDSS_"+out+".fits")
    outfile_r="SDSS_{}_{}_{}r.fits".format(band,str(ra),str(dec))
    montage.mSubimage("SDSS_"+out+".fits",outfile_r,ra,dec,2*margin) # mSubImage takes xsize which should be twice the margin (margin measures center to edge of image)
    shutil.move(outfile_r,os.getcwd()[:-11] )#if change to :-11 then move out of u,g,r,i,z directory, may be more convenient for mJPEG
    if (DEBUG) : print ("Completed Mosaic for " + band)
    os.chdir("../..")
    hdulist = pyfits.open(outfile_r)
    hdulist[0].header['RA']=ra
    hdulist[0].header['DEC']=dec
    hdulist[0].header['PGC']="PGC{}".format(str(pgc))
    hdulist[0].header['NED']=("http://ned.ipac.caltech.edu/cgi-bin/objsearch?objname="+hdulist[0].header['PGC']+"&extend=no&hconst=73&omegam=0.27&omegav=0.73&corr_z=1&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=RA+or+Longitude&of=pre_text&zv_breaker=30000.0&list_limit=5&img_stamp=YES")
    hdulist[0].header['CLEAN']=clean
    outfile="SDSS_{}_{}_{}.fits".format(band,str(ra),str(dec))
    hdulist.writeto(outfile)
    os.system("rm "+outfile_r)
    # for b in bands:
    os.system("rm -r "+band+"/")
    print ("Completed Mosaic")
    return outfile 

def source_info(r_fits_filename):
    '''
    [ra,dec,margin,radius,pgc] ==> Is margin info necessary(?) YES
    Input: Filename String of R band Mosaic fit file
    Returns the updated [ra,dec,margin,radius,pgc] info about the identified RC3 source as a list
    If no RC3 source is identified then [-1,-1,-1,-1,-1] is returned
    '''
    print("Source info for {}".format(r_fits_filename))
    hdulist = pyfits.open(file)
    rc3_ra= hdulist[0].header['RA']
    rc3_dec= hdulist[0].header['DEC']
    # rc3_radius = hdulist[0].header['RADIUS']
    pgc = hdulist[0].header['PGC']
    os.system("sex {} -c default.sex".format(file))
    catalog = open("test.cat",'r')
    # Find max radius and treat as if it is rc3
    #Will have to modify this later to account for multiple neighboring large galaxies
    # Maybe by imposing other RC3-like characteristics (brightness..etc?)
    radius = []
    for line in catalog:
        if (line[0]!='#'):
            radius.append(float(line.split()[1]))
    print (radius)
    #special value that indicate empty list (no object detected by SExtractor)
    radii='@'
    new_ra='@'
    new_dec='@'
    catalog = open("test.cat",'r')
    for i in catalog:
        line = i.split()
        if (line[0]!='#'  and float(line[1])==max(radius) ): 
            print ('Biggest Galaxy with radius {} pixels!'.format(line[1]))
            radii = line[1]
            new_ra= line[2]
            new_dec = line[3]
    print (len(radius)!=0)
    print (radii!='@')
    if (len(radius)!=0 and radii!='@' and float(radii)>4.):
        #treating anything that is 4 pixel or greater as galaxy of interest.
        #radii : pixel to degree conversion
        radii = 0.00010995650106797878*float(radii)
        print ("Radii: {} degrees".format(str(radii)))
        print ("rc3: {} , updated: {} ".format(rc3_ra, new_ra))
        print ("rc3: {} , updated: {} ".format(rc3_dec,new_dec))
        #print ("rc3: {} , updated: {} ".format(rc3_radius,radii))
        updated.write("{}       {}      {}      {}      {} \n".format(rc3_ra,rc3_dec,new_ra,new_dec,radii))
        return [new_ra,new_dec,margin,radii,pgc]
    else: 
        print ("No detected RC3 sources in image. Mosaic using a larger margin")
        # original automated mosaic program default 6*radius
        # call on mosaic program with +50% original margin
        #mosaic_band('r',rc3_ra,rc3_dec,1.5*margin, radius, pgc)
        return [-1,-1,-1,-1,-1,-1]
    #print (radius,new_ra,new_dec)

if __name__ == "__main__":            
    updated = open("rc3_updated.txt",'a') # 'a' for append #'w')
    updated.write("ra       dec         new_ra      new_dec         radius \n")
    os.chdir("..")
    rfits=[file for root, dir, files in os.walk("rfits") for file in files if fnmatch.fnmatchcase(file, "SDSS_r_*.fits")]
    os.chdir("rfits/")
    debug_count=0
    for file in rfits:
        print(file)
        hdulist = pyfits.open(file)
        rc3_ra= hdulist[0].header['RA']
        rc3_dec= hdulist[0].header['DEC']
        pgc = hdulist[0].header['PGC']
        info = source_info(file)
        print (info)
        print ("------------------------------------------------------")
        iteration =0
        while (info ==[-1,-1,-1,-1,-1] and iteration <=3):
            print("#################################################")
            print ("No identified RC3 inside field. Mosaic with +50% margin")
            mosaic_band('r',float(info[0]),float(info[1]),1.5*float(info[2]),float(info[3]),info[4])
            iteration +=1
        #final mosaic (g,r,i color)
        #rc3_radius = hdulist[0].header['RADIUS']
        '''
        if (debug_count<280): #run all for now
            print (file)
            os.system("sex {} -c default.sex".format(file))
            catalog = open("test.cat",'r')
            #find max radius and treat as if it is rc3
            #Will have to modify this later to account for multiple neighboring large galaxies
            # Maybe by imposing other RC3-like characteristics (brightness..etc?)
            radius = []
            for line in catalog:
                if (line[0]!='#'):
                    radius.append(float(line.split()[1]))
            print (radius)
            #print (max(radius)) #breaks if object detected = 0
            #special value that indicate empty list (no object detected by SExtractor)
            radii='@'
            new_ra='@'
            new_dec='@'
            #It seems like I need to "reopen" the file after "using it up" in the above loop
            catalog = open("test.cat",'r')
            if (len(radius)!=0):
                print ("MAX RADIUS: " +str(max(radius)))
            for i in catalog:
                #print("alo")
                line = i.split()
                # print (line[1])
                #print("here1")
                #if (len(radius)!=0):
                    #print("here2")
    #               print(line[1]==str(max(radius)))
                    #float(line[1])==max(radius)
                    #print(float(line[1]))
                    #print(max(radius))
                #print (line[1]==str(max(radius)))
                #print (line[0]!='#')
                #and len(radius)!=0
                if (line[0]!='#'  and float(line[1])==max(radius) ): 
                #treating anything that is 4 pixel or greater as galaxy of interest.
                    print ('Biggest Galaxy with radius {} pixels!'.format(line[1]))
                    radii = line[1]
                    new_ra= line[2]
                    new_dec = line[3]
                    # print (radius,new_ra,new_dec)
            
            # if (radii!='@'):
            #print (float(radii)>4.)
            print (len(radius)!=0)
            print (radii!='@')
            if (len(radius)!=0 and radii!='@' and float(radii)>4.):
                #print ("Radii: "+ str(radii))
                #radii : pixel to degree conversion
                radii = 0.00010995650106797878*float(radii)
                print ("Radii: {} degrees".format(str(radii)))
                print ("rc3: {} , updated: {} ".format(rc3_ra, new_ra))
                print ("rc3: {} , updated: {} ".format(rc3_dec,new_dec))
                #print ("rc3: {} , updated: {} ".format(rc3_radius,radii))
                updated.write("{}       {}      {}      {}      {} \n".format(rc3_ra,rc3_dec,new_ra,new_dec,radii))
            else: 
                print ("No detected RC3 sources in image. Mosaic using a larger margin")
                # original automated mosaic program default 6*radius
                # call on mosaic program with +50% original margin
                #mosaic_band('r',rc3_ra,rc3_dec,1.5*margin, radius, pgc)
                continue
            #print (radius,new_ra,new_dec)
            debug_count += 1
        '''