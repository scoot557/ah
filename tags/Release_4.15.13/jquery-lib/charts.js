var svgns = 'http://www.w3.org/2000/svg';

ratingPhrase = {'-2':'Terrible!',
            '-1':'Dislike',
            '0':'Meh',
            '1':'Solid',
            '2':'Take My Money!'};
var global_drag = '';
var gloval_event = '';
function getMouseXandY (reference, evt){
    var m = reference.getScreenCTM();
    var p = reference.createSVGPoint();
    p.x = evt.clientX;
    p.y = evt.clientY;
    return p.matrixTransform(m.inverse());

}

function Chart(where, data, options){

    var today = new Date(new Date().setHours(0,0,0,0));
    var lastweek = new Date(today.getTime()- (7*86400000));
    if (typeof(options)==="undefined") options={};
    defaults = {
        container_height:   200,
        container_width:    400,
        horizontal_offset:  35,
        vertical_offset:    10,
        path:               false,
        border:             true,
        path_data:          {   bubbles:       true,
                                bubble_radius:  3
                            },
        sliders:            false,
        sliders_data:       {
                                slider_width:   5,
                                shaded:         true,
                                movable:        false,
                                modify_view:    {},
                                stop_handler: function(){return;},
                                slide_handler: function(){return;}
                            },
        volumebars:         false,
        volumebars_data:    {
                                default_spacer: 0.5,
                                max_width:      20
                            },
        axis_data:          {
                                x:          false,
                                y:          false,
                                tickWidth:  5
                            },
        crosshair_data:     {
                                x:  false,
                                y:  false
                            },
        viewMinDate:        lastweek,
        viewMaxDate:        today,
        minrating:          -2,
        maxrating:          2,
        spacer:             {unit:'day',amount:1,format:'mmm d'},
        quickdates:false
    };
    var prop;
    //need to fix this to be recursive.

    for (prop in defaults)
        if (options.hasOwnProperty(prop))
            this[prop] = options[prop];
        else
            this[prop] = defaults[prop];
    this.parent = where;
    this.svgDocument = window.document;
    this.svg = jQuery(this.svgDocument.createElementNS(svgns,'svg'));
    this.svg.attr('version','1.1');
    this.svg.attr('xmlns:svg',svgns);
    this.svg.attr('xmlns',svgns);
    this.parent.append(this.svg);


    this.svg.css({height:this.container_height,width:this.container_width});


    //data should be an object of objects
    //where index = 'yyyy/m/dd'
    //data[index] = { avg: average score of reviews for index,
    //                numrev: number of reviews for index,
    //                dt: new Date(index)
    //              }

    this.data = data;
    this.dragging = false;
    this.drawWidth = this.container_width-(2*this.horizontal_offset);
    this.drawHeight = this.container_height-(2*this.vertical_offset);
    this.viewNumDays = (this.viewMaxDate - this.viewMinDate) / 86400000;

    this.scaleY = function(val) {
        var baseval = val + Math.abs(this.minrating);
        var range = Math.abs(this.minrating) + this.maxrating;
        return parseInt(this.drawHeight * ((range-baseval)/range));
    }
    this.scaleYCounts = function(val, maxval) {
        //returns the drawable height represented by val out of a total maxval.
        return parseInt(this.drawHeight * (1-(val/maxval)));
    }
    this.dragSelect = function(event){
        var scope = event.data.scope;
        var selitem = event.data.element;

        scope.dragging = selitem;
        global_drag = selitem;
        global_event = event;

    }
    this.addDataset = function(ds){
		this.data.append(ds);
	}
    this.dragDeselect = function(event){
        var scope = event.data.scope;
        if (!scope.dragging) return;
        scope.dragging = false;
        scope.sliders_data.stop_handler();

    }
    this.mouseMove = function(event){
        var scope = event.data.scope;
        if (scope.dragging===false) return false
        //take the the start and end point of either:
        // (1) the two sliders
        // or
        // (2) the background rect, if its being drawn
        // or
        // (3) if nothing is selected, draw crosshairs.

        //We're going to need SVG Element specific X and Y values
        var p = getMouseXandY(scope.svg[0], event);

        var movex=p.x;

        if ((p.x + scope.sliders_data.slider_width)<scope.horizontal_offset)
            movex=scope.horizontal_offset - scope.sliders_data.slider_width;
        else if(p.x>(scope.drawWidth + scope.horizontal_offset))
            movex=scope.drawWidth + scope.horizontal_offset;
        //move the slider, get new date ranges, update the view for
        //all componenets in sliders_data.modify_view
        //note - we need to adjust for the rightmost slider to accomodate
        //the width of the slider, and inclusive selection.
        var newdate = scope.xToDate(movex);

        if (scope.dragging!='bg') scope.dragging.setAttribute('x', movex);
        scope.sliders_data.slide_handler();

    }
    this.scaleX = function (dt) {
        var daynum = Math.floor(((dt-this.viewMinDate)/1000)/86400);
        if (dt.getTime()==this.viewMaxDate.getTime()) return this.drawWidth;
        if (this.viewNumDays>0)
            return (this.drawWidth*daynum/this.viewNumDays);
        else
            return (this.drawWidth/2);
    }
    this.setSliderDateRange = function(min, max){
        //leftmost  slider value for calc'ing date is [x + slider_width] (right most point of bar)
        //rightmost slider value for calc'ing date is [x]               (left most point of bar)
        var sliderbars = jQuery('.sliderbar',this.svg);

        var minx = this.scaleX(min);
        if (minx + this.sliders_data.slider_width<this.horizontal_offset) minx=this.horizontal_offset;
        var maxx = this.scaleX(max);
        if (maxx>this.drawWidth) maxx=this.drawWidth;
        sliderbars[0].setAttribute('x',  minx - this.sliders_data.slider_width + this.horizontal_offset);
        sliderbars[1].setAttribute('x', maxx + this.horizontal_offset+1);
        if (this.sliders_data.shaded){
            jQuery('#shadeleft').attr('x2',minx - this.sliders_data.slider_width + this.horizontal_offset);
            jQuery('#shaderight').attr('x1',maxx + this.horizontal_offset);
        }

        this.sliders_data.stop_handler();

    }
    this.viewHandler = function(scope){
        if (typeof scope==='undefined') scope=this;

            var slidervalues = jQuery('.sliderbar',scope.svg);
            var slx1 = parseInt(slidervalues[0].getAttribute('x'));
            var slx2 = parseInt(slidervalues[1].getAttribute('x'));

            if (slx1<slx2) {
                var minval = slx1 + (scope.sliders_data.slider_width);
                var maxval = slx2;

            }
            else{
                var minval = slx2 + (scope.sliders_data.slider_width);
                var maxval = slx1;
            }

            if (scope.sliders_data.shaded){
                jQuery('#shadeleft').attr('x2',minval);
                jQuery('#shaderight').attr('x1',maxval);
            }
            var min = scope.xToDate(minval);
            var max = scope.xToDate(maxval);

            for(var x=0; x<scope.sliders_data.modify_view.length;x++){
                scope.sliders_data.modify_view[x].setView(min, max);
                scope.sliders_data.modify_view[x].refreshComponents();
            }
            scope.sliders_data.slide_handler();

    }
    this.getSliderDateRange = function(){
    //leftmost  slider value for calc'ing date is [x + slider_width] (right most point of bar)
    //rightmost slider value for calc'ing date is [x]               (left most point of bar)
        var sliderbars = jQuery('.sliderbar',this.svg);
        var x1 = parseInt(sliderbars[0].getAttribute('x'));
        var x2 = parseInt(sliderbars[1].getAttribute('x'));
        if (x1<x2){
            var d1 = this.xToDate(x1+this.sliders_data.slider_width);
            var d2 = this.xToDate(x2);
        }
        else{
            var d1 = this.xToDate(x2+this.sliders_data.slider_width);
            var d2 = this.xToDate(x1);
        }
        if (d1<d2)
            return [d1, d2]
        else
            return [d2, d1]

    }
    this.initChart = function(){

        var defs = this.svgDocument.createElementNS(svgns,'defs');
        this.svg.prepend(defs);
        if (this.border){
            var bg_rect = this.svgDocument.createElementNS(svgns, 'rect');
            bg_rect.setAttribute('class','chartbg');
            bg_rect.setAttribute('x',this.horizontal_offset);
            bg_rect.setAttribute('y',this.vertical_offset);
            bg_rect.setAttribute('height',this.drawHeight);
            bg_rect.setAttribute('width',this.drawWidth);
            bg_rect.addEventListener('ondragstart',function(event){event.preventDefault();});
            this.svg.append(bg_rect);
        }


        //path?  add it.
        if (this.path)
            for(var i=0; i<this.data.length; i++)
                this.addPolylinePath(data[i]);

        //volumebars?  add them.
        if (this.volumebars)
            for(var i=0; i<this.data.length; i++)
                this.addVolumeBars(data[i]);
        //check to see if we have an x and y axis
        if (this.axis_data.x) this.addXAxis();
        if (this.axis_data.y) {
			if (this.path) this.addYAxis();
			if (this.volumebars) this.addVolumeLabels();
		}
        //sliders?  add them.
        if (this.sliders) this.addSliders();
        //crosshairs?  add them.
        if (this.crosshair_data.x) this.addMouseCrossHair('x');
        if (this.crosshair_data.y) this.addMouseCrossHair('y');
		if (this.quickdates) this.addQuickDates();
    }
    this.addShade = function(){

        //add two shaded regions to lighten the slider for dates out of range
        //should span from left most drawable region to left most occurring slider
        //from top to bottom of container.
        var shadeline1 = this.svgDocument.createElementNS(svgns,'line');
        var shadeline2 = this.svgDocument.createElementNS(svgns,'line');
        shadeline1.setAttribute('id','shadeleft');
        shadeline1.setAttribute('class','shade');
        shadeline1.setAttribute('x1',this.horizontal_offset);
        shadeline1.setAttribute('x2',this.horizontal_offset);
        shadeline1.setAttribute('y1',this.container_height/2);
        shadeline1.setAttribute('y2',this.container_height/2);
        shadeline1.setAttribute('style','stroke-width: ' + parseInt(this.container_height-(this.vertical_offset*2)) + ';');
        shadeline2.setAttribute('id','shaderight');
        shadeline2.setAttribute('class','shade');
        shadeline2.setAttribute('x1',this.container_width - this.horizontal_offset);
        shadeline2.setAttribute('x2',this.container_width - this.horizontal_offset);
        shadeline2.setAttribute('y1',this.container_height/2);
        shadeline2.setAttribute('y2',this.container_height/2);
        shadeline2.setAttribute('style','stroke-width: ' + parseInt(this.container_height-(this.vertical_offset*2)) + ';');
        this.svg.append(shadeline1);
        this.svg.append(shadeline2);
    }

    this.addQuickDates = function(){
		var qd_div = jQuery('<div>')
						.attr('id','quick_dates');
		var data = {scope:this};
		this.qd = jQuery('<span id="qd_range"></span>');
		qd_div.append(this.qd);
		qd_div.append(jQuery('<a href="javascript:void(0);">1w</a>').addClass('qdBtn').on('click',data,function(event){event.data.scope.setDateByOffset({type:'d',delta:7});}));
		qd_div.append(jQuery('<a href="javascript:void(0);">2w</a>').addClass('qdBtn').on('click',data,function(event){event.data.scope.setDateByOffset({type:'d',delta:14});}));
		qd_div.append(jQuery('<a href="javascript:void(0);">1m</a>').addClass('qdBtn').on('click',data,function(event){event.data.scope.setDateByOffset({type:'m',delta:1});}));
		qd_div.append(jQuery('<a href="javascript:void(0);">3m</a>').addClass('qdBtn').on('click',data,function(event){event.data.scope.setDateByOffset({type:'m',delta:3});}));
		qd_div.append(jQuery('<a href="javascript:void(0);">6m</a>').addClass('qdBtn').on('click',data,function(event){event.data.scope.setDateByOffset({type:'m',delta:6});}));
		this.parent.append(qd_div);
		}
    this.addSliders = function(){

        if (this.sliders_data.shaded)
            this.addShade();
        var slider1 = this.svgDocument.createElementNS(svgns,'rect');
        this.svg.append(slider1);
        slider1.setAttribute('id','slider1');
        slider1.setAttribute('class','sliderbar');
        slider1.setAttribute('x',this.horizontal_offset);
        slider1.setAttribute('y',0);
        slider1.setAttribute('width',this.sliders_data.slider_width);
        slider1.setAttribute('height',this.container_height);

        var slider2 = this.svgDocument.createElementNS(svgns,'rect');
        this.svg.append(slider2);
        slider2.setAttribute('id','slider2');
        slider2.setAttribute('class','sliderbar');
        slider2.setAttribute('x',this.drawWidth + this.horizontal_offset - this.sliders_data.slider_width);
        slider2.setAttribute('y',0);
        slider2.setAttribute('width',this.sliders_data.slider_width);
        slider2.setAttribute('height',this.container_height);


        if (this.sliders_data.movable){
            //attach our listeners that allow this to be dragged.
            //should pass it which elements we are controlling the view of
            //e.g. a list of chart elements.

            //set our event/listener mapping.
            var workers = [ {event:'mousedown', handler:this.dragSelect},
                            {event:'mouseup',   handler:this.dragDeselect}];

            //all the elements to receive these listeners
            var elements = [ slider1, slider2 ];

            //scope so we don't lose this object in the handler function
            var scope = this;


            for (x in elements){
                var element = elements[x];
                jQuery(element).bind('ondragstart',function(event){event.stopPropagation(); event.preventDefault();});
                for (i in workers) {
                    var ev = workers[i].event;
                    var handler = workers[i].handler;
                    var data = {handler: handler, scope:scope, element:element};
                    jQuery(element).bind(ev, data,
                                            function(event){event.stopPropagation(); event.preventDefault(); event.data.handler(event);},
                                            false);
                }
            }
            //our function to handle the movement
            var ev = 'mousemove';
            var handler = this.mouseMove;
            var data = {handler:handler, scope:scope};
            jQuery(document).bind(ev,data,function(event){event.preventDefault();  event.data.handler(event);},false);
            var ev = 'mouseup';
            var handler = this.dragDeselect;
            var data = {handler:handler, scope:scope};
            jQuery(document).bind(ev,data,function(event){event.preventDefault();  event.data.handler(event);},false);


        }
    }
    this.xToDate = function(x) {

        var totaldays = this.viewNumDays;
        var percent = (x-this.horizontal_offset)/this.drawWidth;

        var milliseconds = (totaldays*percent)*86400000;
        var finaldate = new Date(new Date(this.viewMinDate.getTime() + milliseconds).setHours(0,0,0,0));
        return finaldate;

        }

    this.removePolylinePath = function(dataset){
        jQuery('.polyline_path.' + dataset.label,this.svg).remove();
        jQuery('.reviewbubble.' + dataset.label,this.svg).remove();
    }
    this.addPolylinePath = function(dataset){
        //dataset should be a dictionary of objects
        //label:        a label for this dataset
        //data:         a list of objects, index='yyyy/m/dd'
        //              {avg: avgscore, numrev:# of reviews, dt: new Date(index)}
        if (dataset.hidden) return;
        var label = dataset.label;
        var datapoints = dataset.data;

        var polyline_path = this.svgDocument.createElementNS(svgns,'polyline');
        polyline_path.addEventListener("ondragstart",function(event){event.preventDefault();});
        jQuery(polyline_path).insertAfter(jQuery('.chartbg',this.svg));//.prepend(polyline_path);
        var baseClass = 'polyline_path ';
        if (this.sliders) baseClass = 'polyline_path slider_path ';
        polyline_path.setAttribute('class',baseClass + label);
        var path_points = this.generatePath(dataset);
        polyline_path.setAttribute('points', path_points);


    }

    this.updatePolylinePath = function(dataset){
        //data shoul dbe a dictionary of objects
        //indexed by date (yyyy/m/dd)
        //contains: avg, numrev, dt.  (average rating, number of reviews, date)

            this.removePolylinePath(dataset);
            this.addPolylinePath(dataset);
            return;


        var label = dataset.label;
        var datapoints = dataset.data;

        var polyline_path = jQuery('.polyline_path.' + label,this.svg);
        if (polyline_path.length==0) {
            var polyline_path = this.svgDocument.createElementNS(svgns,'polyline');
            polyline_path.setAttribute('class','polyline_path ' + label);
            polyline_path.addEventListener("ondragstart",function(event){event.preventDefault();});
            this.svg.append(polyline_path);
        }
        if (this.path_data.bubbles) jQuery('.reviewbubble.' + label,this.svg).remove();
        var path_points = this.generatePath(data);
        polyline_path.setAttribute('points', path_points);

    }

    this.updateXAxis = function(){
        //sub optimal, but for speed.
        this.removeXAxis();
        this.addXAxis();

    }
    this.updateYAxis = function(){
        //sub optimal, but for speed.
        this.removeYAxis();
        this.addYAxis();

    }
    this.updateVolumeBars = function(dataset){
        //sub optimal, but for speed.
        this.removeVolumeBars(dataset);
        this.addVolumeBars(dataset);

    }

    this.generatePath = function(dataset){
        //data should be a dictionary of objects
        //indexed by date (yyyy/m/dd)
        //contains: avg, numrev, dt.  (average rating, number of reviews, date)
        //dh is the drawable height of the element
        //dw is the drawable width of the element
        var dh = this.drawHeight;
        var dw = this.drawWidth;
        var path_elems = [];
        var data = dataset.data;
        var label = dataset.label;
        var first_point=[], last_point=[];
        var farleft = this.horizontal_offset;
        var farright = this.drawWidth + this.horizontal_offset;
        var bottom = this.drawHeight + this.vertical_offset;
        var top = this.vertical_offset;
        //first_point and last_point are so we can extend the line
        //first_point is the first point historically we can't view,
        //e.g. if the range were 10/21/2012 - 10/28/2012,
        //      a review on 10/20/2012 would yield first_point
        //conversely, last_point is for reviews that are in the future,
        //      relative to the graphs viewMaxDate.
        for (i in data){
            //if the date is prior to our viewarea
            //1st instance: save as the first point
            //2nd and on: if this date is closer to the viewarea boundary
            //            update Y value to reflect more recent data point.
            if (data[i].dt<this.viewMinDate){
                if (first_point.length==0)
                    first_point=[farleft, this.vertical_offset + this.scaleY(data[i].avg), data[i].dt];
                else if (first_point[2]<data[i].dt)
                    first_point=[farleft, this.vertical_offset + this.scaleY(data[i].avg), data[i].dt];
                }
        //if the date is after our viewarea
        //1st instance: save as last point
        //2nd and on:   if this is closer to the viewarea boundary,
        //              update the Y value to reflect more recent data point
            else if (data[i].dt>this.viewMaxDate){
                if (last_point.length==0)
                    last_point=[farright,this.vertical_offset + this.scaleY(data[i].avg), data[i].dt];
                else if (last_point[2]>data[i].dt)
                    last_point=[farright,this.vertical_offset + this.scaleY(data[i].avg), data[i].dt];
                }
            else {
                //This is within the viewable range, add a point.
                var ptx = this.horizontal_offset + this.scaleX(data[i].dt);
                var pty = this.vertical_offset + this.scaleY(data[i].avg);
                path_elems.push([ptx, pty, data[i].dt]);
                }

            }

        if(path_elems.length>0)
            path_elems.sort(function(a, b){return a[0]-b[0];});

        //since we need to extend the line historically
        //not all entities will have a out-of-view datapoint on either side
        //if we didnt' have any points prior to the viewMinDate
        //check and see if we had any on the graph.
        //if no points on graph, check for points >viewMaxDate
        //if there aren't any in first_point, path_elems, and last_point
        //return empty path.

        if (first_point.length==0)
            if (path_elems.length==0)
                if (last_point.length==0)
                    return '';
                else
                    first_point = [farleft, last_point[1]];
            else
                first_point = [farleft, path_elems[0][1]];
        if (last_point.length==0)
            if (path_elems.length==0)
                if (first_point.length==0)
                    return '';
                else
                    last_point = [farright, first_point[1]];
            else
                last_point = [farright, path_elems[path_elems.length-1][1]];

        if (path_elems.length>0){
            if (path_elems[0][0]==first_point[0]) first_point = [];
            if (path_elems[path_elems.length-1][0]==last_point[0]) last_point = [];
        }
        var path_pts='';
        if (this.sliders) {
            //create a first and last point starting at the bottom of the sliderchart
            //for svg fill reasons.
            first_point = [farleft, bottom];
            last_point = [farright, bottom];
        }

        if (first_point.length>0) path_pts = first_point[0] + ' ' + first_point[1] + ' ';
        for (var i = 0; i<path_elems.length; i++){
            path_pts += path_elems[i][0] + ' ' + path_elems[i][1] + ' ';
            if (this.path_data.bubbles) this.addBubble(path_elems[i][2].getTime(), path_elems[i][0], path_elems[i][1], label)
        }
        if (last_point.length>0) path_pts += last_point[0] + ' ' + last_point[1];
        return path_pts;
    }
    this.removeYAxis = function(){
        jQuery('.y-axis',this.svg).remove();
        jQuery('.y-axis-line',this.svg).remove();
        jQuery('.y-axis-tick',this.svg).remove();
        jQuery('.y-axis-label',this.svg).remove();
    }
    this.addYAxis = function(){
        var yAxis = this.svgDocument.createElementNS(svgns,'g');
        yAxis.setAttribute('class','y-axis');
        this.svg.append(yAxis);
        var yAxisLine = this.svgDocument.createElementNS(svgns,'line');
        var yAxisTicks = [];
        var yAxisLabels = [];

        yAxisLine.setAttribute('class','y-axis-line');
        yAxisLine.setAttribute('x1',parseInt(this.horizontal_offset) - 0.5);
        yAxisLine.setAttribute('x2',parseInt(this.horizontal_offset) - 0.5);
        yAxisLine.setAttribute('y1',parseInt(this.vertical_offset));
        yAxisLine.setAttribute('y2',parseInt(this.vertical_offset+this.drawHeight));
        yAxis.appendChild(yAxisLine);
        //y scale is integer based.  no fancy calcs
        //-2, -1, 0, 1, 2
        numratings = this.maxrating + Math.abs(this.minrating);
        for (var y=this.minrating; y<=this.maxrating; y++) {
            var yAxisTick = this.svgDocument.createElementNS(svgns,'line');
            yAxisTick.setAttribute('class','y-axis-tick');
            yValue = this.scaleY(y)+this.vertical_offset;
            yAxisTick.setAttribute('x1',parseInt(this.horizontal_offset-(this.axis_data.tickWidth/2)));
            yAxisTick.setAttribute('x2',parseInt(this.horizontal_offset+(this.axis_data.tickWidth/2)));
            yAxisTick.setAttribute('y1',yValue);
            yAxisTick.setAttribute('y2',yValue);
            yAxis.appendChild(yAxisTick);

            var yAxisLabel = this.svgDocument.createElementNS(svgns,'text');
            yAxisLabel.setAttribute('class','y-axis-label');
            yAxisLabel.setAttribute('x',0);
            yAxisLabel.setAttribute('y',0);
            yAxisLabel.textContent=ratingPhrase[parseInt(y)];
            //we have to render this first, or FF will shit bricks.
            yAxis.appendChild(yAxisLabel);
            var yAxisLabelHeight = yAxisLabel.getBBox().height;
            var yAxisLabelWidth = yAxisLabel.getBBox().width;
            yAxisLabel.setAttribute('x',this.horizontal_offset - yAxisLabelWidth - (this.axis_data.tickWidth/2));
            yAxisLabel.setAttribute('y',yValue + (yAxisLabelHeight/3));


            yAxisTicks.push(yAxisTick);
            yAxisLabels.push(yAxisLabel);
            //yAxis.appendChild(yAxisTick);
            yAxisLabel.addEventListener("ondragstart",function(event){event.preventDefault();});

        }

    }
	this.addVolumeLabels = function(){
        var yAxis = this.svgDocument.createElementNS(svgns,'g');
        yAxis.setAttribute('class','y-axis');
        this.svg.append(yAxis);
        var yAxisLine = this.svgDocument.createElementNS(svgns,'line');
        var yAxisTicks = [];
        var yAxisLabels = [];

        yAxisLine.setAttribute('class','y-axis-line');
        yAxisLine.setAttribute('x1',parseInt(this.horizontal_offset) - 0.5);
        yAxisLine.setAttribute('x2',parseInt(this.horizontal_offset) - 0.5);
        yAxisLine.setAttribute('y1',parseInt(this.vertical_offset));
        yAxisLine.setAttribute('y2',parseInt(this.vertical_offset+this.drawHeight));
        yAxis.appendChild(yAxisLine);
        //y scale is integer based.  no fancy calcs
        //-2, -1, 0, 1, 2
        var maxrev = this.data[0].max_reviews;
        //two tick marks, halfway and max.
        var halfway = Math.floor(maxrev/2);
        var ticks = [halfway, maxrev];
        for (var x=0; x<=2; x++) {
            var y = ticks[x];
            var yAxisTick = this.svgDocument.createElementNS(svgns,'line');
            yAxisTick.setAttribute('class','y-axis-tick');
            yValue = this.scaleYCounts(y,maxrev)+this.vertical_offset;
            yAxisTick.setAttribute('x1',parseInt(this.horizontal_offset-(this.axis_data.tickWidth/2)));
            yAxisTick.setAttribute('x2',parseInt(this.horizontal_offset+(this.axis_data.tickWidth/2)));
            yAxisTick.setAttribute('y1',yValue);
            yAxisTick.setAttribute('y2',yValue);
            yAxis.appendChild(yAxisTick);

            var yAxisLabel = this.svgDocument.createElementNS(svgns,'text');
            yAxisLabel.setAttribute('class','y-axis-label');
            yAxisLabel.setAttribute('x',0);
            yAxisLabel.setAttribute('y',0);
            if (y!=1)
				yAxisLabel.textContent=y + ' reviews';
			else
				yAxisLabel.textContent=y + ' review';
            //we have to render this first, or FF will shit bricks.
            yAxis.appendChild(yAxisLabel);
            var yAxisLabelHeight = yAxisLabel.getBBox().height;
            var yAxisLabelWidth = yAxisLabel.getBBox().width;
            yAxisLabel.setAttribute('x',this.horizontal_offset - yAxisLabelWidth - (this.axis_data.tickWidth/2));
            yAxisLabel.setAttribute('y',yValue + (yAxisLabelHeight/3));
			console.log(yValue + (yAxisLabelHeight));

            yAxisTicks.push(yAxisTick);
            yAxisLabels.push(yAxisLabel);
            //yAxis.appendChild(yAxisTick);
            yAxisLabel.addEventListener("ondragstart",function(event){event.preventDefault();});

        }
    }
    this.removeVolumeBars = function(dataset){
        jQuery('.barchart_bar.' + dataset.label, this.svg).remove();
    }
    this.addVolumeBars = function(dataset){
        if (dataset.hidden) return;
        //dataset should be a dictionary of objects
        //label:        a label for this dataset
        //data:         a list of objects, index='yyyy/m/dd'
        //              {avg: avgscore, numrev:# of reviews, dt: new Date(index)}
        var label = dataset.label;
        var datapoints = dataset.data;
        var bars = this.generateVolumeBars(datapoints);
        for(var x=0;x<bars.length;x++){
            //add a line to barchart
            var newbar = this.svgDocument.createElementNS(svgns, "line");
            newbar.setAttribute('x1',bars[x][0]);
            newbar.setAttribute('y1',this.drawHeight + this.vertical_offset);
            newbar.setAttribute('x2',bars[x][0]);
            newbar.setAttribute('y2',bars[x][2]);
            newbar.setAttribute('revs',bars[x][4]);
            newbar.setAttribute('class','barchart_bar ' + label);
            newbar.addEventListener('mousemove',function(event){event.currentTarget.setAttribute('opacity','0.5');});
            newbar.addEventListener('mouseout',function(event){event.currentTarget.setAttribute('opacity','1.0')});
            this.svg.append(newbar);
        }
        this.resizeBars();
    }

    this.resizeBars = function(){
        jQuery('.barchart_bar', this.svg).css('stroke-width',this.barwidth());
        var bars = this;
		jQuery.each(
			jQuery('.barchart_bar', this.svg),
			function(i, val){
				var lb=bars.horizontal_offset;
				var rb = bars.drawWidth+bars.horizontal_offset;
				var bar_width = parseInt(jQuery(this).css('stroke-width'));
				var bar_left = parseInt(jQuery(this).attr('x1')) - parseInt(bar_width/2);
				var bar_right = parseInt(jQuery(this).attr('x1')) + parseInt(bar_width/2);
				if (bar_left<bars.horizontal_offset) {
					var newwidth = (bar_right-bars.horizontal_offset);
					jQuery(this).css('stroke-width', newwidth+'px');
					jQuery(this).attr('x1', bars.horizontal_offset+(newwidth/2));
					jQuery(this).attr('x2', bars.horizontal_offset+(newwidth/2));
				}
				else if (bar_right>bars.horizontal_offset+bars.drawWidth) {
					var newwidth = (bars.drawWidth+bars.horizontal_offset - bar_left);
					jQuery(this).css('stroke-width', newwidth+'px');
					jQuery(this).attr('x1', bars.horizontal_offset+bars.drawWidth - (newwidth/2));
					jQuery(this).attr('x2', bars.horizontal_offset+bars.drawWidth - (newwidth/2));
				}
				
			});

    }
    this.barwidth = function(){
        var bc_h_offset = this.horizontal_offset;
        var bc_numdays = this.viewNumDays;
        var bc_space = this.volumebars_data.default_spacer;
        var max_width = this.volumebars_data.max_width;
        var available_pixels = this.drawWidth;
        var bw = (available_pixels - (bc_numdays * bc_space)) / (bc_numdays);
        if (bw>max_width) bw=max_width;
        return bw;
    }
    this.updateQuickDates = function(){
		var drange = this.getSliderDateRange();
		var min = drange[0].format('mmm dd, yyyy');
		var max = drange[1].format('mmm dd, yyyy');
		this.qd.html(min + ' - '  + max);
	}
    this.generateVolumeBars = function(data){
        //make this chart relative, not review relative
        var maxrev=-1;
        for(i in data){if(data[i].numrev>maxrev) maxrev=data[i].numrev;}

        var bars = [];
        for (i in data){
                var dtindex = new Date(i);
            if (dtindex>=this.viewMinDate && dtindex<=this.viewMaxDate){
                var numRevs = data[i].numrev;
                //function ratingToY(rating, cheight,cvertical_offset, minRating, maxRating)
                var barheight = this.scaleYCounts(numRevs, maxrev) + this.vertical_offset;
                var bar_y = this.drawHeight+this.vertical_offset;
                var bar_x = this.scaleX(dtindex) + this.horizontal_offset;
                bars.push([bar_x,bar_y,barheight,this.barwidth(),numRevs]);
            }
        }
        return bars;
    }
    this.removeXAxis = function(){
        jQuery('.x-axis',this.svg).remove();
        jQuery('.x-axis-line',this.svg).remove();
        jQuery('.x-axis-tick',this.svg).remove();
        jQuery('.x-axis-label',this.svg).remove();
    }
    this.addXAxis = function (){

        var xAxis = this.svgDocument.createElementNS(svgns,'g');
        xAxis.setAttribute('class','x-axis');
        var xAxisLine = this.svgDocument.createElementNS(svgns,'line');
        var xAxisTicks = [];
        var xAxisLabels = [];
        var maxticks = 7;
        this.svg.append(xAxis);
        xAxisLine.setAttribute('x1',parseInt(this.horizontal_offset));
        xAxisLine.setAttribute('x2',parseInt(this.drawWidth+this.horizontal_offset));
        xAxisLine.setAttribute('y1',parseInt(this.vertical_offset+(this.drawHeight/2)));
        xAxisLine.setAttribute('y2',parseInt(this.vertical_offset+(this.drawHeight/2)));
        xAxisLine.setAttribute('class','x-axis-line');
        xAxisLine.addEventListener("ondragstart",function(event){event.preventDefault();});
        xAxis.appendChild(xAxisLine);
        number_of_days = Math.ceil(((this.viewMaxDay-this.viewMinDay)/1000)/86400);
        //spacer = daysbetween(number_of_days, 1, 1, maxticks);
        cdate = new Date(this.viewMaxDate);
        ndate = this.priorTick(cdate);
        cdate = ndate;
        var counter=0;

        while (cdate>this.viewMinDate) {
            counter+=1;
            var xAxisTick = this.svgDocument.createElementNS(svgns,'line');
            var xAxisLabel = this.svgDocument.createElementNS(svgns,'text');
            var xValue = this.scaleX(cdate) + this.horizontal_offset;
            var xValueLabel = cdate.format(this.spacer.format);

            var labelYValue = parseInt(this.vertical_offset+(this.drawHeight));
            xAxis.appendChild(xAxisTick);
            xAxisTick.setAttribute('x1',xValue-0.5);
            xAxisTick.setAttribute('x2',xValue-0.5);
            xAxisTick.setAttribute('y1',parseInt(this.vertical_offset+(this.drawHeight)-(this.axis_data.tickWidth*0.5)));
            xAxisTick.setAttribute('y2',parseInt(this.vertical_offset+(this.drawHeight)+(this.axis_data.tickWidth*0.5)));
            xAxisTick.setAttribute('class','x-axis-tick');
            xAxisLabel.setAttribute('class','x-axis-label');
            //xAxisLabel.setAttribute('transform','rotate(70, ' + xValue + ', ' + labelYValue + ')');
            //we have to draw it first, so IE and FF don't shit bricks
            xAxisLabel.textContent = xValueLabel;
            xAxisLabel.setAttribute('x',0);
            xAxisLabel.setAttribute('y',0);
            xAxis.appendChild(xAxisLabel);
            console.log(xAxisLabel.getBBox().height);

            xAxisLabelWidth = xAxisLabel.getBBox().width;
            xAxisLabelHeight = xAxisLabel.getBBox().height;
            xAxisLabel.setAttribute('x',parseInt(xValue)-parseInt(xAxisLabelWidth/2));
            xAxisLabel.setAttribute('y',parseInt(labelYValue)+(xAxisLabelHeight));

            xAxisTicks.push(xAxisTick);
            xAxisLabels.push(xAxisLabel);
            xAxisLabel.addEventListener("ondragstart",function(event){event.preventDefault();});
            xAxisTick.addEventListener("ondragstart",function(event){event.preventDefault();});
            //log([cdate]);
            ndate = this.priorTick(cdate);
            cdate = ndate;
            }

            //cdate = new Date(startDay);

    }
    this.priorTick = function(dt){
        var spacer = this.spacer;
        var newdate = new Date(dt);
        if (spacer.unit=='day')
            var newdate = new Date(dt.getTime()-(this.spacer.amount * 86400000));
        else if (spacer.unit=='month')
            {
                if (spacer.amount==0.5){

                    if (dt.getDate()>15){
                        newday=15;
                        newmonth=dt.getMonth();
                        newyear=dt.getFullYear();
                    }
                    else if (dt.getDate()>1){
                        newday=1;
                        newmonth=dt.getMonth();
                        newyear=dt.getFullYear();
                        }
                    else if (dt.getDate()==1){
                        newday=15;
                        if(cdate.getMonth()>0){
                            newmonth=dt.getMonth()-1;
                            newyear=dt.getFullYear();
                        }
                        else {
                            newmonth=11;
                            newyear=dt.getFullYear()-1;
                        }
                    }
                }
                //multi-month spacing.
                else {
                    if(dt.getDate()!=1) {
                        newyear=dt.getFullYear();
                        newmonth=dt.getMonth();
                        newday=1;
                    } else{
                        newday=1;
                        newyear=dt.getFullYear();
                        if((dt.getMonth()+1)>=spacer.amount)
                        newmonth=dt.getMonth()-spacer.amount;

                        else{
                            newmonth=dt.getMonth()+12-spacer.amount;
                            newyear-=1;
                        }
                    }
                }

                var newdate = new Date(newyear, newmonth, newday ,0,0,0);

            }
       return newdate;
    }
    this.xLabel = function (dt){
        if (this.viewNumDays<60)
            datestring = dt.format('mmm dd');
        else
            datestring = dt.format('mmm dd');

        return datestring;
    }

    this.generateBubble = function (){
        var altercircle = this.svgDocument.createElementNS(svgns,'circle');
        altercircle.setAttribute('cx',0);
        altercircle.setAttribute('cy',0);
        altercircle.setAttribute('r',this.path_data.bubble_radius);

        return altercircle;
    }
    this.addBubble = function (id, cx, cy, label){

        var bubbleid=id;

        var newbubble = jQuery('#' + id);
        if (newbubble.length==0){
            newbubble = this.generateBubble();
            newbubble.setAttribute('class','reviewbubble ' + label);
            newbubble.setAttribute('id',id);
            this.svg.append(newbubble);
        }
        else newbubble[0].setAttribute('class','reviewbubble ' + label);
        this.moveBubble(newbubble,cx,cy);
    }

    this.moveBubble = function(bub, new_cx, new_cy) {
            var new_x_value = new_cx - this.path_data.bubble_radius;
            var new_y_value = new_cy - this.path_data.bubble_radius;
            jQuery(bub).attr('cx',new_cx);
            jQuery(bub).attr('cy',new_cy);
            if (new_cx<this.horizontal_offset || new_cx > this.drawWidth+this.horizontal_offset)
                jQuery(bub).attr('display','none');
            else
                jQuery(bub).attr('display','inline');

        }
    this.moveMouseCH = function(event){
        var non = {x:'y',y:'x'};
        var axis = event.data.axis;
        var element = event.data.element;
        var ch = jQuery("#mouse-ch-" + axis, jQuery(element));

        var pts = getMouseXandY(element, event);
        if (axis=='y') p = pts.x;
        else p = pts.y;
        ch.attr(non[axis] + '1',p);
        ch.attr(non[axis] + '2',p);
    }

    this.addMouseCrossHair = function(axis){

        var mouseAxisLine = this.svgDocument.createElementNS(svgns,'line');
        mouseAxisLine.setAttribute('id','mouse-ch-' + axis);
        mouseAxisLine.setAttribute('class','mouse-ch');
        var non = {x:'y',y:'x'};

        if (non[axis]=='x')
            n = this.container_height;
        else
            n = this.container_width;

        mouseAxisLine.setAttribute(non[axis] + '1',0);
        mouseAxisLine.setAttribute(non[axis] + '2', 0);
        mouseAxisLine.setAttribute(axis + '1',0);
        mouseAxisLine.setAttribute(axis + '2',n);
        this.svg.append(mouseAxisLine);
        var handler = this.moveMouseCH;
        var element = this.svg[0];
        this.svg.bind('mousemove',
            {axis:axis, element:element, handler: handler},
            function(event){
                event.data.handler(event);
                });
    }
	this.setDateByOffset = function(date_offset){
		//takes current most recent date, and extends view historically
		//by date_offset
		//format: {type,delta}
		// where type is 'd' or 'm' for days or months (respectively)
		// and delta is the offset
		
		var max = new Date(this.getSliderDateRange()[1]);
		var newmin = new Date(max);
		if (date_offset.type == 'd')
			newmin.setDate(newmin.getDate()-date_offset.delta);
		else if (date_offset.type == 'm')
			newmin.setMonth(newmin.getMonth()-date_offset.delta);
		this.setSliderDateRange(newmin,max);
	}
	this.setView = function(min, max){
        this.viewMinDate = new Date(min);
        this.viewMaxDate = new Date(max);
        this.viewNumDays = (this.viewMaxDate - this.viewMinDate) / 86400000;
        switch(true){
            case this.viewNumDays < 9:
                this.spacer.unit = 'day';
                this.spacer.amount = 1;
                this.spacer.format = 'mmm d';
                break;
            case this.viewNumDays < 18:
                this.spacer.unit = 'day';
                this.spacer.amount = 2;
                this.spacer.format = 'mmm d';
                break;
            case this.viewNumDays < 27:
                this.spacer.unit = 'day';
                this.spacer.amount = 3;
                this.spacer.format = 'mmm d';
                break;
        //if it is between 10 and 50 days of data - weekly ticks, daily grouping.
            case this.viewNumDays < 63:
                this.spacer.unit = 'day';
                this.spacer.amount = 7;
                this.spacer.format = 'mmm d';
                break;
            case this.viewNumDays<135:
                this.spacer.unit = 'month'
                this.spacer.amount = 0.5;
                this.spacer.format = 'mmm d';
                break;
        //if it is between 140 and 356 - mounthly ticks, weekly groupings.
            case this.viewNumDays<270:
                this.spacer.unit = 'month'
                this.spacer.amount = 1;
                this.spacer.format = "mmm 'yy";
                break;
            case this.viewNumDays<820:
                this.spacer.unit = 'month'
                this.spacer.amount = 3;
                this.spacer.format = "mmm 'yy";
                break;
            default:
                this.spacer.unit = 'month'
                this.spacer.amount = 6;
                this.spacer.format = "mmm 'yy";
                break;
        }
    }
    this.refreshComponents = function(){
        //sliders don't automatically move.  they are set by user.
		
        //path?  update them.  all of them.
        if (this.path)
            for(var i=0; i<this.data.length; i++)
                this.updatePolylinePath(data[i]);

        //volumebars?  update them.  all of them.
        if (this.volumebars)
            for(var i=0; i<this.data.length; i++)
                this.updateVolumeBars(data[i]);

        //check to see if we have an x, if so - update it.
        if (this.axis_data.x) this.updateXAxis();
        if (this.quickdates) this.updateQuickDates();
        //y axis doesn't change.
        //if (this.axis_data.y) this.updateYAxis();

    }


    this.initChart();
}

