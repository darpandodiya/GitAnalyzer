var activesheets; 

function initViz() {
    var div1 = document.getElementById("dashboard");
    var url1 = "https://public.tableau.com/views/GitAnalyzerDashboard/MainDashboard?:embed=y&:display_count=yes&publish=yes";
	
    
    var options = {
        hideTabs: true,
        hideToolbar: true,
        showShareOptions: false,
        onFirstInteractive: () => {  
            activesheets = viz.getWorkbook().getActiveSheet().getWorksheets();  
       }
    };

    var viz = new tableau.Viz(div1, url1,options);


}

$(initViz);
