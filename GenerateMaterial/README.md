## The symbolic link named `Master`
Inside `GenerateMaterial` directory, there is a symbolic link named `Master`. This `Master` is linked to the directory where the master notebooks in the course are stored. In this case, it is linked to `../master`.  If one decides to store master notebooks somewhere else, one can link it to a different directory (but not recommended). If you have a good reason to do so, one can do that by removing this `Master` link and creating a new one that will be linked to a correct directory by using the following commands:-

To remove the link:

		rm Master

To create the link and link it to the correct directory:
	

		ln -s <...YourPathToExtractedNotebookDirectory...> ./Master

> The link name is not restricted just only to `Master`. One can use a different name.
	
For example,
	
		rm Master
		ln -s ../MyDir/MyMaster ./Master
	
After this, one should edit the key `notebook_folder` in `config.json` in `AssignmentNotebook` accordingly.
