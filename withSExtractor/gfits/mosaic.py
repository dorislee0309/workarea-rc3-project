import montage_wrapper as montage
from astropy.io import fits as pyfits
import os
import shutil
from math import trunc
import sqlcl
import sys 
DEBUG = True
# n = 0
# start=False
# output = open("rc3_galaxies_outside_SDSS_footprint.txt",'a') # 'a' for append #'w')
# unclean = open("rc3_galaxies_unclean","a")

# class Mosaic():
class Mosaic:
    def __init__(self):
        # self.data = []
        pass
    def mosaic (ra,dec,margin,radius,pgc,clean=True):
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
            output.write("{}     {}     {}     {} \n".format(str(ra),str(dec),str(radius),pgc))
            sys.exit()
            # break
        else :
            if (DEBUG): 
                print ( "Complete Query. These data lies within margin: ")
                print (data)
        os.mkdir(filename)
        os.chdir(filename)
        bands=['u','g','r','i','z']
        for band in bands:
            os.mkdir(band)
            os.chdir(band)
            os.mkdir ("raw")
            os.mkdir ("projected")
            os.chdir("raw")
            if (DEBUG): print ("Retrieving data from SDSS SAS server for "+ band +"band")
            for i in data :  
                #out = "frame-"+str(band)+"-"+str(i[0]).zfill(6)+"-"+str(i[1])+"-"+str(i[2]).zfill(4)
                out = "frame-{}-{}-{}-{}".format(str(band),str(i[0]).zfill(6),str(i[1]),str(i[2]).zfill(4))
                #os.system("wget http://mirror.sdss3.org/sas/dr10/boss/photoObj/frames/301/"+str(i[0])+"/"+ str(i[1]) +"/"+out+".fits.bz2")
                os.system("wget http://mirror.sdss3.org/sas/dr10/boss/photoObj/frames/301/{}/{}/{}.fits.bz2".format(str(i[0]),str(i[1]),out) )
                #os.system("bunzip2 "+out+".fits.bz2")
                os.system("bunzip2 {}.fits.bz2".format(out))
            # print (os.getcwd())
            os.chdir("../")
            if (DEBUG) : print("Creating mosaic for {} band.".format(band))
            montage.mImgtbl("raw","images.tbl")
            #montage.mHdr(str(ra)+" "+str(dec),margin,out+".hdr")
            montage.mHdr("{} {}".format(str(ra),str(dec)),margin,"{}.hdr".format(out))
            if (DEBUG): print ("Reprojecting images")
            #Sometimes you can't find the files and result in images.tbl => empty doc
            #need to put data file inside raw AND unzip it so that Montage detect that it is a fit file
            os.chdir("raw")
            montage.mProjExec("../images.tbl","../"+out+".hdr","../projected", "../stats.tbl") 
            os.chdir("..")
            montage.mImgtbl("projected","pimages.tbl")
            #mAdd coadds the reprojected images using the FITS header template and mImgtbl list.
            os.chdir("projected")
            montage.mAdd("../pimages.tbl","../"+out+".hdr","SDSS_"+out+".fits")
            outfile_r="SDSS_{}_{}_{}r.fits".format(band,str(ra),str(dec))
            montage.mSubimage("SDSS_"+out+".fits",outfile_r,ra,dec,2*margin) # mSubImage takes xsize which should be twice the margin (margin measures center to edge of image)
            shutil.move(outfile_r,os.getcwd()[:-11] )#if change to :-11 then move out of u,g,r,i,z directory, may be more convenient for mJPEG
            if (DEBUG) : print ("Completed Mosaic for " + band)
            #Writing PGC number into FITS header information
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
        # Superimposing R,G,B image mosaics into TIFF using STIFF
        # Image for Viewing purposes
        os.system("stiff  SDSS_i_{0}_{1}.fits  SDSS_r_{0}_{1}.fits SDSS_g_{0}_{1}.fits  -c stiff.conf  -OUTFILE_NAME  SDSS_{0}_{1}_BEST.tiff    -MAX_TYPE QUANTILE  -MAX_LEVEL 0.99 -COLOUR_SAT  6 -MIN_TYPE QUANTILE -MIN_LEVEL 1  -GAMMA_FAC 0.7 ".format(str(ra),str(dec)))
        # Image for emphasizing low-surface sturcture
        os.system("stiff  SDSS_i_{0}_{1}.fits  SDSS_r_{0}_{1}.fits SDSS_g_{0}_{1}.fits  -c stiff.conf  -OUTFILE_NAME  SDSS_{0}_{1}_LOW.tiff  -MAX_TYPE QUANTILE  -MAX_LEVEL 0.98 -COLOUR_SAT  5  -MIN_TYPE QUANTILE -MIN_LEVEL 0.01  -GAMMA_FAC 0.9 ".format(str(ra),str(dec)))  
        os.system("rm stiff.xml")
        for b in bands:
            os.system("rm -r "+b+"/")
        print ("Completed Mosaic")